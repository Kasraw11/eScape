from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


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


class RefugeSummary(BaseModel):
    refuge_id: int
    name: str
    category: str
    address: str | None = None
    latitude: float
    longitude: float
    distance_m: int
    estimated_travel_minutes: int
    opening_status: str
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
