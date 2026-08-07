from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes import get_optional_db
from app.repositories.refuge_repository import RefugeRepository
from app.schemas.refuges import RefugeCategory, RefugeDetails, RefugeFeedbackCreate, RefugeFeedbackCreated, RefugeFeedbackSummary, RefugeSearchResponse
from app.services.refuge_feedback_service import RefugeFeedbackService, RefugeNotFoundError
from app.services.refuge_search_service import RefugeSearchService


router = APIRouter(prefix="/api/refuges", tags=["refuges"])


def get_refuge_search_service(db: Session | None = Depends(get_optional_db)) -> RefugeSearchService | None:
    return RefugeSearchService(RefugeRepository(db)) if db is not None else None


def get_refuge_feedback_service(db: Session | None = Depends(get_optional_db)) -> RefugeFeedbackService | None:
    return RefugeFeedbackService(RefugeRepository(db)) if db is not None else None


@router.get("", response_model=RefugeSearchResponse)
def search_refuges(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=100, le=5000)] = 1000,
    category: RefugeCategory | None = None,
    selected_datetime: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    service: RefugeSearchService | None = Depends(get_refuge_search_service),
) -> RefugeSearchResponse:
    if service is None:
        raise HTTPException(status_code=503, detail="Refuge search requires a configured database")
    try:
        return service.search(latitude, longitude, radius_m, category, selected_datetime, limit)
    except Exception as exc:
        service.repository.db.rollback()
        raise HTTPException(status_code=503, detail="Refuge data is temporarily unavailable") from exc


@router.get("/{refuge_id}", response_model=RefugeDetails)
def refuge_details(
    refuge_id: int,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    selected_datetime: datetime | None = None,
    service: RefugeSearchService | None = Depends(get_refuge_search_service),
) -> RefugeDetails:
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be provided together")
    if service is None:
        raise HTTPException(status_code=503, detail="Refuge search requires a configured database")
    result = service.details(refuge_id, latitude, longitude, selected_datetime)
    if result is None:
        raise HTTPException(status_code=404, detail="Sensory refuge was not found")
    return result


@router.get("/{refuge_id}/feedback/summary", response_model=RefugeFeedbackSummary)
def refuge_feedback_summary(
    refuge_id: int,
    service: RefugeFeedbackService | None = Depends(get_refuge_feedback_service),
) -> RefugeFeedbackSummary:
    if service is None:
        raise HTTPException(status_code=503, detail="Community feedback is temporarily unavailable")
    try:
        return service.summary(refuge_id)
    except RefugeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Sensory refuge was not found") from exc
    except Exception as exc:
        service.repository.db.rollback()
        raise HTTPException(status_code=503, detail="Community feedback is temporarily unavailable") from exc


@router.post("/{refuge_id}/feedback", response_model=RefugeFeedbackCreated, status_code=status.HTTP_201_CREATED)
def submit_refuge_feedback(
    refuge_id: int,
    payload: RefugeFeedbackCreate,
    service: RefugeFeedbackService | None = Depends(get_refuge_feedback_service),
) -> RefugeFeedbackCreated:
    if service is None:
        raise HTTPException(status_code=503, detail="Community feedback is temporarily unavailable")
    try:
        return service.submit(refuge_id, payload)
    except RefugeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Sensory refuge was not found") from exc
    except Exception as exc:
        service.repository.db.rollback()
        raise HTTPException(status_code=503, detail="Feedback could not be submitted") from exc
