from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.pedestrian_repository import PedestrianCountRecord
from app.services.data_freshness_service import DataFreshnessService, FreshnessStatus, ensure_aware, least_fresh
from app.services.sensor_matching_service import SegmentSensorMatch


DEFAULT_CROWD_THRESHOLD = 3
DEFAULT_HISTORICAL_BASELINE_COUNT = 300.0
LOW_CROWD_MAX_COUNT = 20
MEDIUM_CROWD_MAX_COUNT = 40
MINIMUM_SENSOR_COVERAGE_RATIO = 0.5
PREFERENCE_SCORE_LIMITS = {
    1: 0.55,
    2: 0.80,
    3: 1.00,
    4: 1.25,
    5: 1.50,
}


def acceptable_congestion_score(preference_level: int | None) -> float:
    return PREFERENCE_SCORE_LIMITS.get(preference_level or DEFAULT_CROWD_THRESHOLD, PREFERENCE_SCORE_LIMITS[DEFAULT_CROWD_THRESHOLD])


@dataclass(frozen=True)
class SegmentScore:
    segment_sequence: int
    matched_sensor_count: int
    score: float | None
    congestion_level: str | None
    data_availability: str
    weight: float
    pedestrian_count: int | None
    threshold_exceeded: bool | None
    data_source: str
    observed_at: datetime | None
    freshness_status: FreshnessStatus


@dataclass(frozen=True)
class RouteScore:
    sensory_score: float | None
    sensory_indicator: str
    data_availability: str
    matched_sensor_count: int
    sensor_coverage_ratio: float
    warning_message: str | None
    segment_scores: list[SegmentScore]
    threshold_exceeded: bool | None
    qualifies_preference: bool
    data_freshness: FreshnessStatus
    observed_at: datetime | None
    updated_at: datetime


class SensoryScoringService:
    """Score pedestrian exposure using counts and historical baselines.

    Each covered segment is the mean of its matched sensors' normalised
    congestion values. A sensor uses its same-period historical baseline when
    available, otherwise the documented conservative fallback of 300
    pedestrians. Route scores are distance-weighted segment means. Raw average
    segment counts of 0-20 are Low, 21-40 are Medium, and 41 or more are High.
    Preference levels map to explicit acceptable score limits via
    ``PREFERENCE_SCORE_LIMITS``.
    """

    def __init__(self, freshness_service: DataFreshnessService | None = None) -> None:
        self.freshness_service = freshness_service or DataFreshnessService()

    def score_route(
        self,
        segment_matches: list[SegmentSensorMatch],
        counts_by_sensor: dict[int, PedestrianCountRecord],
        crowd_threshold: int | None,
        historical_baselines: dict[int, float] | None = None,
        now: datetime | None = None,
    ) -> RouteScore:
        current_time = ensure_aware(now or datetime.now(timezone.utc)) or datetime.now(timezone.utc)
        baselines = historical_baselines or {}
        preference_limit = acceptable_congestion_score(crowd_threshold)
        segment_scores: list[SegmentScore] = []
        weighted_scores: list[tuple[float, float]] = []
        matched_sensor_ids: set[int] = set()
        total_segments = len(segment_matches)

        for segment_match in segment_matches:
            matched_sensor_ids.update(match.sensor.sensor_id for match in segment_match.matched_sensors)
            segment_weight = float(segment_match.distance_m or 1)
            records = [
                counts_by_sensor[match.sensor.sensor_id]
                for match in segment_match.matched_sensors
                if match.sensor.sensor_id in counts_by_sensor
            ]

            if not records:
                segment_scores.append(
                    SegmentScore(
                        segment_sequence=segment_match.segment_sequence,
                        matched_sensor_count=len(segment_match.matched_sensors),
                        score=None,
                        congestion_level=None,
                        data_availability="unavailable",
                        weight=segment_weight,
                        pedestrian_count=None,
                        threshold_exceeded=None,
                        data_source="unavailable",
                        observed_at=None,
                        freshness_status="unavailable",
                    )
                )
                continue

            normalised_values = []
            for record in records:
                baseline = baselines.get(record.sensor_id) or DEFAULT_HISTORICAL_BASELINE_COUNT
                normalised_values.append(record.total_count / max(1.0, float(baseline)))

            segment_score = round(sum(normalised_values) / len(normalised_values), 2)
            average_count = round(sum(record.total_count for record in records) / len(records))
            freshnesses = [
                self.freshness_service.classify(record.observed_at, record.source, current_time)
                for record in records
            ]
            observed_values = [ensure_aware(record.observed_at) for record in records]
            observed_at = max(value for value in observed_values if value is not None)
            source = "realtime" if any(record.source == "realtime" for record in records) else "historical"
            threshold_exceeded = segment_score > preference_limit

            weighted_scores.append((segment_score, segment_weight))
            segment_scores.append(
                SegmentScore(
                    segment_sequence=segment_match.segment_sequence,
                    matched_sensor_count=len(segment_match.matched_sensors),
                    score=segment_score,
                    congestion_level=self._congestion_level(average_count),
                    data_availability="available",
                    weight=segment_weight,
                    pedestrian_count=average_count,
                    threshold_exceeded=threshold_exceeded,
                    data_source=source,
                    observed_at=observed_at,
                    freshness_status=least_fresh(freshnesses),
                )
            )

        scored_segments = [segment for segment in segment_scores if segment.score is not None]
        coverage_ratio = round(len(scored_segments) / total_segments, 2) if total_segments else 0.0

        if not weighted_scores:
            return RouteScore(
                sensory_score=None,
                sensory_indicator="Unavailable",
                data_availability="unavailable",
                matched_sensor_count=len(matched_sensor_ids),
                sensor_coverage_ratio=coverage_ratio,
                warning_message=(
                    "Pedestrian sensor data is unavailable for this route, so congestion information cannot be fully "
                    "confirmed and personalised recommendations cannot be generated."
                ),
                segment_scores=segment_scores,
                threshold_exceeded=None,
                qualifies_preference=False,
                data_freshness="unavailable",
                observed_at=None,
                updated_at=current_time,
            )

        route_freshness = least_fresh([segment.freshness_status for segment in scored_segments])
        observed_at = max(segment.observed_at for segment in scored_segments if segment.observed_at is not None)
        total_weight = sum(weight for _, weight in weighted_scores)
        route_score = round(sum(score * weight for score, weight in weighted_scores) / total_weight, 2)
        weighted_counts = [
            (segment.pedestrian_count, segment.weight)
            for segment in scored_segments
            if segment.pedestrian_count is not None
        ]
        route_average_pedestrian_count = (
            round(sum(count * weight for count, weight in weighted_counts) / total_weight)
            if weighted_counts
            else None
        )
        threshold_exceeded = any(segment.threshold_exceeded is True for segment in scored_segments)

        warning_message = None
        availability = "available" if len(scored_segments) == total_segments else "partial"
        if coverage_ratio < MINIMUM_SENSOR_COVERAGE_RATIO:
            route_score = None
            availability = "partial"
            warning_message = "Pedestrian data coverage is too limited for personalised route recommendations."
        elif len(scored_segments) != total_segments:
            warning_message = "Pedestrian data is partial for this route, so congestion information cannot be fully confirmed."
        elif route_freshness == "stale":
            warning_message = "The latest pedestrian readings are stale; current congestion cannot be fully confirmed."
        elif route_freshness == "historical":
            warning_message = "This route uses historical pedestrian data rather than live conditions."

        if route_score is None:
            indicator = "Unavailable"
            threshold_value: bool | None = None
            qualifies = False
        else:
            indicator = (
                "Unavailable"
                if route_average_pedestrian_count is None
                else self._congestion_level(route_average_pedestrian_count).title()
            )
            threshold_value = threshold_exceeded
            qualifies = not threshold_exceeded

        return RouteScore(
            sensory_score=route_score,
            sensory_indicator=indicator,
            data_availability=availability,
            matched_sensor_count=len(matched_sensor_ids),
            sensor_coverage_ratio=coverage_ratio,
            warning_message=warning_message,
            segment_scores=segment_scores,
            threshold_exceeded=threshold_value,
            qualifies_preference=qualifies,
            data_freshness=route_freshness,
            observed_at=observed_at,
            updated_at=current_time,
        )

    @staticmethod
    def _congestion_level(pedestrian_count: int) -> str:
        if pedestrian_count <= LOW_CROWD_MAX_COUNT:
            return "low"
        if pedestrian_count <= MEDIUM_CROWD_MAX_COUNT:
            return "medium"
        return "high"
