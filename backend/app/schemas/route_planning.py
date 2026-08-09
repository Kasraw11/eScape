from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator


MELBOURNE_CBD_LATITUDE_RANGE = (-37.8350, -37.7900)
MELBOURNE_CBD_LONGITUDE_RANGE = (144.9350, 144.9900)


class RoutePlanningRequest(BaseModel):
    # Starting coordinates.
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)

    # Destination coordinates.
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)

    # Temporary backend default.
    # The frontend no longer asks the user to choose a travel mode.
    # Later this can be replaced by multimodal route planning.
    travel_mode: Literal["walking", "transit"] = "walking"

    # Internal default used by the sensory scoring system.
    crowd_threshold: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias=AliasChoices(
            "preferred_crowd_threshold",
            "crowd_threshold",
        ),
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
            raise ValueError(
                "Origin and destination must be different"
            )

        if not (min_lat <= self.origin_latitude <= max_lat):
            raise ValueError(
                "Origin latitude is outside the supported Melbourne CBD boundary"
            )

        if not (min_lng <= self.origin_longitude <= max_lng):
            raise ValueError(
                "Origin longitude is outside the supported Melbourne CBD boundary"
            )

        if not (min_lat <= self.destination_latitude <= max_lat):
            raise ValueError(
                "Destination latitude is outside the supported Melbourne CBD boundary"
            )

        if not (min_lng <= self.destination_longitude <= max_lng):
            raise ValueError(
                "Destination longitude is outside the supported Melbourne CBD boundary"
            )

        return self


class MatchedSensorResponse(BaseModel):
    sensor_id: int
    sensor_name: str
    latitude: float
    longitude: float
    pedestrian_count: int | None = None
    observed_at: datetime | None = None


class RouteSegmentResponse(BaseModel):
    route_segment_id: int | None = None

    segment_sequence: int

    encoded_polyline: str | None = None

    # Route geometry as latitude/longitude pairs.
    points: list[tuple[float, float]] = Field(
        default_factory=list
    )

    distance_m: int | None = None
    duration_seconds: int | None = None

    matched_sensor_count: int = 0

    congestion_level: str | None = None
    sensory_score: float | None = None

    data_availability: str | None = None
    pedestrian_count: int | None = None

    threshold_exceeded: bool = False

    data_source: str | None = None

    observed_at: datetime | None = None

    freshness_status: str | None = None

    matched_sensors: list[MatchedSensorResponse] = Field(default_factory=list)


class RouteOptionResponse(BaseModel):
    route_id: int | None = None

    route_identifier: str

    encoded_polyline: str | None = None

    # Full route geometry returned by OSRM.
    points: list[tuple[float, float]] = Field(
        default_factory=list
    )

    estimated_travel_minutes: int

    travel_mode: Literal["walking", "transit"] = "walking"

    sensory_score: float | None = None

    sensory_indicator: str | None = None

    is_recommended: bool = False

    pedestrian_data_availability: str | None = None

    data_availability_status: str | None = None

    matched_sensor_count: int = 0

    sensor_coverage_ratio: float | None = None

    route_segments: list[RouteSegmentResponse] = Field(
        default_factory=list
    )

    warning_message: str | None = None

    threshold_exceeded: bool = False

    qualifies_preference: bool = False

    recommendation_explanation: str | None = None

    data_freshness: str | None = None

    observed_at: datetime | None = None

    updated_at: datetime | None = None


class RoutePlanResponse(BaseModel):
    recommended_route_identifier: str | None = None

    routes: list[RouteOptionResponse]

    preferred_crowd_threshold: int = 3

    threshold_message: str | None = None

    all_routes_high: bool = False

    personalised_recommendations_available: bool = False
