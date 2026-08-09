from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routes import get_optional_db
from app.repositories.pedestrian_repository import PedestrianRepository
from app.schemas.predictions import (
    MinimumSeverity,
    PredictionSearchResponse,
    PredictiveAlertSearchResponse,
)
from app.services.melbourne_pedestrian_service import (
    MelbournePedestrianService,
)
from app.services.prediction_query_service import (
    PredictionQueryService,
)


router = APIRouter(
    prefix="/api",
    tags=["predictions"],
)


def get_prediction_query_service(
    db: Session | None = Depends(get_optional_db),
) -> PredictionQueryService | None:
    """
    Creates the prediction query service when
    a database connection is available.

    If the database is disabled, prediction
    endpoints will return a 503 response.
    """

    if db is None:
        return None

    return PredictionQueryService(db)


@router.get(
    "/predictions",
    response_model=PredictionSearchResponse,
)
def get_predictions(
    latitude: Annotated[
        float,
        Query(ge=-90, le=90),
    ],
    longitude: Annotated[
        float,
        Query(ge=-180, le=180),
    ],
    radius_m: Annotated[
        int,
        Query(ge=100, le=5000),
    ] = 1000,
    forecast_minutes: Annotated[
        int,
        Query(ge=1, le=60),
    ] = 60,
    minimum_severity: MinimumSeverity = MinimumSeverity.LOW,
    service: PredictionQueryService | None = Depends(
        get_prediction_query_service
    ),
) -> PredictionSearchResponse:
    """
    Returns predicted crowd/sensory conditions
    near a requested location.

    This endpoint currently requires the database.
    """

    if service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction services are "
                "temporarily unavailable."
            ),
        )

    try:
        return service.predictions(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            forecast_minutes=forecast_minutes,
            minimum_severity=minimum_severity,
        )

    except Exception as exc:
        service.db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction services are "
                "temporarily unavailable."
            ),
        ) from exc


@router.get(
    "/alerts/predictive",
    response_model=PredictiveAlertSearchResponse,
)
def get_predictive_alerts(
    latitude: Annotated[
        float,
        Query(ge=-90, le=90),
    ],
    longitude: Annotated[
        float,
        Query(ge=-180, le=180),
    ],
    enabled: bool = True,
    minimum_severity: MinimumSeverity = MinimumSeverity.HIGH,
    maximum_distance_m: Annotated[
        int,
        Query(ge=100, le=5000),
    ] = 1000,
    route_only: bool = False,
    service: PredictionQueryService | None = Depends(
        get_prediction_query_service
    ),
) -> PredictiveAlertSearchResponse:
    """
    Returns predictive alerts near the user.

    This endpoint currently requires the database.
    """

    if service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction services are "
                "temporarily unavailable."
            ),
        )

    try:
        return service.alerts(
            latitude=latitude,
            longitude=longitude,
            enabled=enabled,
            minimum_severity=minimum_severity,
            maximum_distance_m=maximum_distance_m,
            route_only=route_only,
        )

    except Exception as exc:
        service.db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction services are "
                "temporarily unavailable."
            ),
        ) from exc


@router.get("/pedestrian-test")
async def pedestrian_test():
    """
    Temporary development endpoint.

    Tests whether eScape can retrieve pedestrian
    sensor information directly from the City of
    Melbourne Open Data API without PostgreSQL.
    """

    try:
        service = MelbournePedestrianService()

        return await service.get_sensor_locations()

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to retrieve Melbourne "
                "pedestrian sensor data."
            ),
        ) from exc


@router.post("/pedestrian-sync")
async def pedestrian_sync(
    db: Session | None = Depends(get_optional_db),
):
    """
    Fetch the latest City of Melbourne pedestrian
    data and save it into PostgreSQL.

    This endpoint is temporary and is used to test
    the pedestrian data pipeline during development.
    """

    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        )

    repository = PedestrianRepository(db)

    service = MelbournePedestrianService(
        repository=repository,
    )

    try:
        result = await service.sync_to_database()

        return {
            "status": "ok",
            **result,
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to sync Melbourne "
                "pedestrian data."
            ),
        ) from exc