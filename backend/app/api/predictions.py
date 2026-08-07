from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routes import get_optional_db
from app.schemas.predictions import (
    MinimumSeverity,
    PredictionSearchResponse,
    PredictiveAlertSearchResponse,
)
from app.services.prediction_query_service import PredictionQueryService


router = APIRouter(prefix="/api", tags=["predictions"])


def get_prediction_query_service(db: Session | None = Depends(get_optional_db)) -> PredictionQueryService | None:
    return PredictionQueryService(db) if db is not None else None


@router.get("/predictions", response_model=PredictionSearchResponse)
def get_predictions(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=100, le=5000)] = 1000,
    forecast_minutes: Annotated[int, Query(ge=1, le=60)] = 60,
    minimum_severity: MinimumSeverity = MinimumSeverity.LOW,
    service: PredictionQueryService | None = Depends(get_prediction_query_service),
) -> PredictionSearchResponse:
    if service is None:
        raise HTTPException(status_code=503, detail="Prediction services are temporarily unavailable.")
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
        raise HTTPException(status_code=503, detail="Prediction services are temporarily unavailable.") from exc


@router.get("/alerts/predictive", response_model=PredictiveAlertSearchResponse)
def get_predictive_alerts(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    enabled: bool = True,
    minimum_severity: MinimumSeverity = MinimumSeverity.HIGH,
    maximum_distance_m: Annotated[int, Query(ge=100, le=5000)] = 1000,
    route_only: bool = False,
    service: PredictionQueryService | None = Depends(get_prediction_query_service),
) -> PredictiveAlertSearchResponse:
    if service is None:
        raise HTTPException(status_code=503, detail="Prediction services are temporarily unavailable.")
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
        raise HTTPException(status_code=503, detail="Prediction services are temporarily unavailable.") from exc
