from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SUPPORTED_TRAVEL_MODES = {"walking", "transit"}
MELBOURNE_CBD_LATITUDE_RANGE = (-37.8255, -37.8050)
MELBOURNE_CBD_LONGITUDE_RANGE = (144.9440, 144.9765)


class RoutePlanningRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)
    travel_mode: Literal["walking", "transit"]
    crowd_threshold: int | None = Field(default=None, ge=1, le=5)

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
    segment_sequence: int
    encoded_polyline: str | None = None
    distance_m: int | None = None
    duration_seconds: int | None = None
    matched_sensor_count: int
    congestion_level: str | None = None
    sensory_score: float | None = None
    data_availability: str


class RouteOptionResponse(BaseModel):
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


class RoutePlanResponse(BaseModel):
    recommended_route_identifier: str | None
    routes: list[RouteOptionResponse]
