from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator


SUPPORTED_TRAVEL_MODES = {"walking", "transit"}
MELBOURNE_CBD_LATITUDE_RANGE = (-37.8255, -37.8050)
MELBOURNE_CBD_LONGITUDE_RANGE = (144.9440, 144.9765)


class RoutePlanningRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)
    travel_mode: Literal["walking", "transit"]
    crowd_threshold: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias=AliasChoices("preferred_crowd_threshold", "crowd_threshold"),
    )

    @property
    def preferred_crowd_threshold(self) -> int:
        return self.crowd_threshold

    @model_validator(mode="after")
    def validate_supported_area(self) -> "RoutePlanningRequest":
        min_lat, max_lat = MELBOURNE_CBD_LATITUDE_RANGE
        min_lng, max_lng = MELBOURNE_CBD_LONGITUDE_RANGE
        if (
            self.origin_latitude == self.destination_latitude
            and self.origin_longitude == self.destination_longitude
        ):
            raise ValueError("Origin and destination must be different")
        if not (min_lat <= self.origin_latitude <= max_lat):
            raise ValueError("Origin latitude is outside the supported Melbourne CBD boundary")
        if not (min_lng <= self.origin_longitude <= max_lng):
            raise ValueError("Origin longitude is outside the supported Melbourne CBD boundary")
        if not (min_lat <= self.destination_latitude <= max_lat):
            raise ValueError("Destination latitude is outside the supported Melbourne CBD boundary")
        if not (min_lng <= self.destination_longitude <= max_lng):
            raise ValueError("Destination longitude is outside the supported Melbourne CBD boundary")
        return self


class RouteSegmentResponse(BaseModel):
    route_segment_id: int | None = None
    segment_sequence: int
    encoded_polyline: str | None = None
    distance_m: int | None = None
    duration_seconds: int | None = None
    matched_sensor_count: int
    congestion_level: str | None = None
    sensory_score: float | None = None
    data_availability: str
    pedestrian_count: int | None = None
    threshold_exceeded: bool | None = None
    data_source: str = "unavailable"
    observed_at: datetime | None = None
    freshness_status: Literal["live", "recent", "historical", "stale", "unavailable"] = "unavailable"


class RouteOptionResponse(BaseModel):
    route_id: int | None = None
    route_identifier: str
    encoded_polyline: str | None = None
    estimated_travel_minutes: int
    travel_mode: Literal["walking", "transit"]
    sensory_score: float | None = None
    sensory_indicator: str
    is_recommended: bool
    pedestrian_data_availability: str
    data_availability_status: str
    matched_sensor_count: int
    sensor_coverage_ratio: float
    route_segments: list[RouteSegmentResponse]
    warning_message: str | None = None
    threshold_exceeded: bool | None = None
    qualifies_preference: bool = False
    recommendation_explanation: str | None = None
    data_freshness: Literal["live", "recent", "historical", "stale", "unavailable"] = "unavailable"
    observed_at: datetime | None = None
    updated_at: datetime | None = None


class RoutePlanResponse(BaseModel):
    recommended_route_identifier: str | None
    routes: list[RouteOptionResponse]
    preferred_crowd_threshold: int = 3
    threshold_message: str | None = None
    all_routes_high: bool = False
    personalised_recommendations_available: bool = True


class CongestionAlternativeResponse(BaseModel):
    route_id: int
    route_identifier: str
    sensory_score: float
    sensory_indicator: str
    estimated_travel_minutes: int
    threshold_exceeded: bool
    recommendation_explanation: str


class CongestionNotificationResponse(BaseModel):
    change_key: str
    route_id: int
    route_segment_id: int | None = None
    segment_sequence: int | None = None
    congestion_level: str
    threshold_exceeded: bool
    updated_at: datetime
    message: str


class RouteCongestionResponse(BaseModel):
    route_id: int
    route_identifier: str
    congestion_status: str
    sensory_score: float | None = None
    sensory_indicator: str
    threshold_exceeded: bool | None = None
    preferred_crowd_threshold: int
    updated_at: datetime
    data_freshness: Literal["live", "recent", "historical", "stale", "unavailable"]
    route_segments: list[RouteSegmentResponse]
    alternatives: list[CongestionAlternativeResponse] = Field(default_factory=list)
    meaningful_change: bool = False
    notification: CongestionNotificationResponse | None = None
    warning_messages: list[str] = Field(default_factory=list)
