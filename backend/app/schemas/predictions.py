from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


PREDICTION_UNAVAILABLE_MESSAGE = "Prediction services are temporarily unavailable."


class MinimumSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PredictionResponse(BaseModel):
    prediction_id: int
    sensor_id: int
    location_name: str
    latitude: float
    longitude: float
    distance_m: int
    prediction_for: datetime
    predicted_count: int | None
    severity: str
    confidence: str
    generated_at: datetime
    source_data_freshness: str
    data_availability_status: str
    limitation_message: str | None = None
    data_source: str
    source_validated: bool
    route_relevant: bool = False


class PredictionSearchResponse(BaseModel):
    service_available: bool
    predictions: list[PredictionResponse]
    forecast_minutes: int
    generated_at: datetime | None = None
    message: str | None = None


class PredictiveAlertResponse(BaseModel):
    alert_id: int
    deduplication_key: str
    prediction_id: int
    sensor_id: int
    location_name: str
    latitude: float
    longitude: float
    distance_m: int
    predicted_time: datetime
    severity: str
    confidence: str
    message: str
    suggested_action: str
    route_impact: str
    status: str
    updated_at: datetime
    data_freshness: str
    source_validated: bool


class PredictiveAlertSearchResponse(BaseModel):
    service_available: bool
    alerts: list[PredictiveAlertResponse]
    preferences_temporary: bool = True
    message: str | None = None
