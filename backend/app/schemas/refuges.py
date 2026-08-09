from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RefugeCategory(str, Enum):
    PARK = "park"
    LIBRARY = "library"
    QUIET_PUBLIC_SPACE = "quiet_public_space"
    INDOOR_QUIET_SPACE = "indoor_quiet_space"


CATEGORY_LABELS = {
    RefugeCategory.PARK: "Park",
    RefugeCategory.LIBRARY: "Library",
    RefugeCategory.QUIET_PUBLIC_SPACE: "Quiet public space",
    RefugeCategory.INDOOR_QUIET_SPACE: "Indoor quiet space",
}


class RefugeOpeningStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class RefugeSummary(BaseModel):
    refuge_id: int
    name: str
    category: RefugeCategory

    address: str | None = None

    latitude: float
    longitude: float

    distance_m: int
    estimated_travel_minutes: int

    opening_status: RefugeOpeningStatus
    opening_hours_summary: str | None = None

    sensory_suitability_description: str

    data_source: str | None = None
    data_last_updated: datetime | None = None

    limitation_message: str


class RefugeDetails(RefugeSummary):
    sensory_notes: str | None = None
    accessibility_notes: str | None = None
    operating_hours: str | None = None
    source_record_id: str | None = None


class RefugeSearchResponse(BaseModel):
    results: list[RefugeSummary]
    result_count: int
    radius_m: int
    selected_datetime: datetime
    message: str | None = None


class RefugeCrowdingLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class RefugeComfortLevel(str, Enum):
    YES = "yes"
    SOMEWHAT = "somewhat"
    NO = "no"


class RefugeFeedbackCreate(BaseModel):
    quietness_score: int = Field(ge=1, le=5)
    crowding_level: RefugeCrowdingLevel
    comfort_level: RefugeComfortLevel
    comment: str | None = Field(default=None, max_length=300)


class RefugeFeedbackCreated(BaseModel):
    feedback_id: int
    refuge_id: int
    created_at: datetime


class RefugeFeedbackSummary(BaseModel):
    refuge_id: int
    response_count: int

    average_quietness: float | None = None
    quiet_percentage: int | None = None
    comfortable_percentage: int | None = None
    low_crowding_percentage: int | None = None

    crowding_distribution: dict[str, int]