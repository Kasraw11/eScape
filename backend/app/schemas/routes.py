from pydantic import BaseModel, Field

from app.core.crowd import CrowdLevel
from app.core.validation import Coordinate, MelbournePlaceInput


class RoutePlanRequest(BaseModel):
    origin: MelbournePlaceInput
    destination: MelbournePlaceInput
    crowd_threshold: CrowdLevel = Field(
        default=CrowdLevel.MEDIUM,
        description="Maximum crowd level the user is comfortable with.",
    )


class RouteSegment(BaseModel):
    start: Coordinate
    end: Coordinate
    sensory_level: CrowdLevel


class RouteOption(BaseModel):
    route_id: str
    title: str
    summary: str
    distance_m: int
    estimated_duration_min: int
    sensory_level: CrowdLevel
    sensory_level_rank: int
    high_congestion_segments: int
    medium_congestion_segments: int
    sensor_coverage: str
    matched_sensor_count: int = 0
    average_pedestrian_count: int | None = None
    max_pedestrian_count: int | None = None
    data_source: str
    recommendation_reason: str
    is_recommended: bool
    segments: list[RouteSegment]


class RoutePlanResponse(BaseModel):
    status: str
    message: str
    requested_threshold: CrowdLevel
    origin: Coordinate | None = None
    destination: Coordinate | None = None
    data_confidence: str = "limited"
    limitations: list[str] = []
    routes: list[RouteOption] = []
