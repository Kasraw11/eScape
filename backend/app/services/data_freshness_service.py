from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Literal

from app.config import settings


FreshnessStatus = Literal["live", "recent", "historical", "stale", "unavailable"]


def ensure_aware(value: datetime | date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DataFreshnessService:
    def __init__(
        self,
        live_window_seconds: int | None = None,
        recent_window_seconds: int | None = None,
    ) -> None:
        self.live_window_seconds = live_window_seconds or settings.pedestrian_live_window_seconds
        self.recent_window_seconds = recent_window_seconds or settings.pedestrian_recent_window_seconds

    def classify(
        self,
        observed_at: datetime | date | None,
        source: str | None,
        now: datetime | None = None,
    ) -> FreshnessStatus:
        if observed_at is None or not source:
            return "unavailable"
        if source == "historical":
            return "historical"

        observed = ensure_aware(observed_at)
        current = ensure_aware(now or datetime.now(timezone.utc))
        if observed is None or current is None:
            return "unavailable"

        age_seconds = max(0.0, (current - observed).total_seconds())
        if age_seconds <= self.live_window_seconds:
            return "live"
        if age_seconds <= self.recent_window_seconds:
            return "recent"
        return "stale"


def least_fresh(statuses: list[FreshnessStatus]) -> FreshnessStatus:
    if not statuses:
        return "unavailable"
    rank = {"live": 0, "recent": 1, "historical": 2, "stale": 3, "unavailable": 4}
    return max(statuses, key=lambda status: rank[status])
