from __future__ import annotations

import json
import math
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.repositories.refuge_repository import RefugeRepository
from app.schemas.refuges import CATEGORY_LABELS, RefugeCategory, RefugeDetails, RefugeSearchResponse, RefugeSummary
from app.services.sensor_matching_service import haversine_meters


MELBOURNE_TIMEZONE = ZoneInfo("Australia/Melbourne")
REFUGE_LIMITATION = "Sensory refuge candidate. Quietness is not guaranteed; conditions may change." 


def normalize_selected_datetime(value: datetime | None) -> datetime:
    selected = value or datetime.now(MELBOURNE_TIMEZONE)
    if selected.tzinfo is None:
        selected = selected.replace(tzinfo=MELBOURNE_TIMEZONE)
    return selected.astimezone(MELBOURNE_TIMEZONE)


def opening_status(opening_hours: str | None, selected: datetime) -> tuple[str, str | None]:
    if not opening_hours:
        return "hours_unavailable", None
    try:
        schedule = json.loads(opening_hours)
    except (json.JSONDecodeError, TypeError):
        return "hours_unavailable", opening_hours
    if not isinstance(schedule, dict):
        return "hours_unavailable", None

    local = normalize_selected_datetime(selected)
    day_periods = schedule.get(local.strftime("%A").lower())
    if day_periods is None:
        return "hours_unavailable", _hours_summary(schedule)
    if not isinstance(day_periods, list):
        return "hours_unavailable", _hours_summary(schedule)
    if not day_periods:
        return "closed", _hours_summary(schedule)

    for period in day_periods:
        if not isinstance(period, list) or len(period) != 2:
            continue
        try:
            opens = time.fromisoformat(str(period[0]))
            closes = time.fromisoformat(str(period[1]))
        except ValueError:
            continue
        current = local.timetz().replace(tzinfo=None)
        if (opens <= closes and opens <= current < closes) or (opens > closes and (current >= opens or current < closes)):
            return "open", _hours_summary(schedule)
    return "closed", _hours_summary(schedule)


def _hours_summary(schedule: dict[str, Any]) -> str:
    parts = []
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        periods = schedule.get(day)
        if periods is None:
            continue
        label = day[:3].title()
        if not periods:
            parts.append(f"{label} closed")
            continue
        valid = [f"{period[0]}–{period[1]}" for period in periods if isinstance(period, list) and len(period) == 2]
        if valid:
            parts.append(f"{label} {', '.join(valid)}")
    return "; ".join(parts)


class RefugeSearchService:
    def __init__(self, repository: RefugeRepository) -> None:
        self.repository = repository

    def search(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        category: RefugeCategory | None,
        selected_datetime: datetime | None,
        limit: int,
    ) -> RefugeSearchResponse:
        selected = normalize_selected_datetime(selected_datetime)
        category_label = CATEGORY_LABELS[category] if category else None
        candidates = self.repository.list_candidates(latitude, longitude, radius_m, category_label)
        results = []
        for refuge in candidates:
            distance = haversine_meters(
                (latitude, longitude),
                (float(refuge.latitude), float(refuge.longitude)),
            )
            if distance <= radius_m:
                results.append(self._summary(refuge, distance, selected))
        results.sort(key=lambda refuge: (refuge.distance_m, refuge.name.casefold()))
        results = results[:limit]
        return RefugeSearchResponse(
            results=results,
            result_count=len(results),
            radius_m=radius_m,
            selected_datetime=selected,
            message=(
                None
                if results
                else "No sensory refuge candidates were found within this radius. Try increasing the search radius."
            ),
        )

    def details(
        self,
        refuge_id: int,
        latitude: float | None,
        longitude: float | None,
        selected_datetime: datetime | None,
    ) -> RefugeDetails | None:
        refuge = self.repository.get(refuge_id)
        if refuge is None:
            return None
        distance = (
            haversine_meters((latitude, longitude), (float(refuge.latitude), float(refuge.longitude)))
            if latitude is not None and longitude is not None
            else 0.0
        )
        summary = self._summary(refuge, distance, normalize_selected_datetime(selected_datetime))
        return RefugeDetails(
            **summary.model_dump(),
            sensory_notes=refuge.sensory_notes,
            accessibility_notes=refuge.accessibility_notes,
            operating_hours=refuge.opening_hours,
            source_record_id=refuge.source_record_id,
        )

    @staticmethod
    def _summary(refuge, distance: float, selected: datetime) -> RefugeSummary:
        status, hours_summary = opening_status(refuge.opening_hours, selected)
        sensory_description = refuge.sensory_notes or "Potential quiet space; conditions have not been independently verified."
        return RefugeSummary(
            refuge_id=refuge.poi_id,
            name=refuge.feature_name,
            category=refuge.theme or "Quiet public space",
            address=refuge.address,
            latitude=float(refuge.latitude),
            longitude=float(refuge.longitude),
            distance_m=round(distance),
            estimated_travel_minutes=max(1, math.ceil(distance / 80)),
            opening_status=status,
            opening_hours_summary=hours_summary,
            sensory_suitability_description=sensory_description,
            data_source=refuge.source,
            data_last_updated=refuge.last_updated_at,
            limitation_message=REFUGE_LIMITATION,
        )
