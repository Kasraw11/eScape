from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.data_freshness_service import DataFreshnessService, ensure_aware


MODEL_LIMITATION = (
    "Deterministic estimate from a matched historical baseline and recent trend; "
    "events, weather and sensor outages are not modelled."
)


@dataclass(frozen=True)
class TimedCount:
    total_count: int
    observed_at: datetime


@dataclass(frozen=True)
class PredictionCalculation:
    prediction_for: datetime
    predicted_count: int | None
    severity: str
    confidence: str
    source_freshness: str
    data_availability_status: str
    limitation_message: str
    source_validated: bool
    historical_baseline: float | None
    trend_adjustment: float | None


def is_validated_city_source(source: str | None) -> bool:
    normalized = " ".join((source or "").casefold().split())
    development_markers = ("sample", "mock", "synthetic", "fixture", "test data")
    if not normalized or any(marker in normalized for marker in development_markers):
        return False
    return (
        normalized == "city of melbourne open data"
        or normalized.startswith("city of melbourne open data:")
        or normalized == "city of melbourne pedestrian counting system"
        or "data.melbourne.vic.gov.au" in normalized
    )


class PredictionCalculator:
    def __init__(self, freshness_service: DataFreshnessService | None = None) -> None:
        self.freshness_service = freshness_service or DataFreshnessService()

    def calculate(
        self,
        *,
        prediction_for: datetime,
        generated_at: datetime,
        recent_counts: list[TimedCount],
        historical_counts: list[int],
        sensor_source: str | None,
    ) -> PredictionCalculation:
        target = ensure_aware(prediction_for) or prediction_for.replace(tzinfo=timezone.utc)
        now = ensure_aware(generated_at) or generated_at.replace(tzinfo=timezone.utc)
        source_validated = is_validated_city_source(sensor_source)
        if not source_validated:
            return self._unavailable(target, "Sensor source is not validated as City of Melbourne Open Data.", False)
        if not historical_counts:
            return self._unavailable(target, "No matching historical weekday/hour records are available.", True)
        if not recent_counts:
            return self._unavailable(target, "No current pedestrian reading is available.", True)

        ordered = sorted(recent_counts, key=lambda item: item.observed_at, reverse=True)
        latest = ordered[0]
        freshness = self.freshness_service.classify(latest.observed_at, "realtime", now)
        baseline = sum(historical_counts) / len(historical_counts)
        if baseline <= 0:
            return self._unavailable(target, "The matching historical baseline is zero or invalid.", True)

        trend_adjustment = 0.0
        trend_stable = True
        if len(ordered) >= 2:
            previous = ordered[1]
            elapsed_minutes = max(1.0, (ensure_aware(latest.observed_at) - ensure_aware(previous.observed_at)).total_seconds() / 60)
            horizon_minutes = max(0.0, (target - now).total_seconds() / 60)
            raw_trend = ((latest.total_count - previous.total_count) / elapsed_minutes) * horizon_minutes
            cap = baseline * 0.5
            trend_adjustment = max(-cap, min(cap, raw_trend))
            trend_stable = abs(latest.total_count - previous.total_count) <= baseline * 0.5

        predicted_count = max(0, round((baseline * 0.5) + (latest.total_count * 0.5) + trend_adjustment))
        ratio = predicted_count / baseline
        severity = "Low" if ratio < 0.8 else "Moderate" if ratio < 1.25 else "High"

        if len(historical_counts) >= 8 and freshness == "live" and len(ordered) >= 2 and trend_stable:
            confidence = "High"
        elif len(historical_counts) >= 3 and freshness in {"live", "recent"}:
            confidence = "Medium"
        else:
            confidence = "Low"

        limitations = [MODEL_LIMITATION]
        if freshness == "stale":
            limitations.append("The latest current reading is stale, so confidence is Low.")
        elif confidence == "Low":
            limitations.append("Limited samples or an unstable trend reduce confidence.")
        return PredictionCalculation(
            prediction_for=target,
            predicted_count=predicted_count,
            severity=severity,
            confidence=confidence,
            source_freshness=freshness,
            data_availability_status="available",
            limitation_message=" ".join(limitations),
            source_validated=True,
            historical_baseline=round(baseline, 1),
            trend_adjustment=round(trend_adjustment, 1),
        )

    @staticmethod
    def _unavailable(target: datetime, message: str, source_validated: bool) -> PredictionCalculation:
        return PredictionCalculation(
            prediction_for=target,
            predicted_count=None,
            severity="Unavailable",
            confidence="Low",
            source_freshness="unavailable",
            data_availability_status="unavailable",
            limitation_message=message,
            source_validated=source_validated,
            historical_baseline=None,
            trend_adjustment=None,
        )
