from __future__ import annotations

from dataclasses import dataclass

from app.repositories.pedestrian_repository import PedestrianCountRecord
from app.services.sensor_matching_service import SegmentSensorMatch


DEFAULT_CROWD_THRESHOLD = 3
HIGH_SENSORY_SCORE_THRESHOLD = 1.5
MINIMUM_SENSOR_COVERAGE_RATIO = 0.5


@dataclass(frozen=True)
class SegmentScore:
    segment_sequence: int
    matched_sensor_count: int
    score: float | None
    congestion_level: str | None
    data_availability: str
    weight: float


@dataclass(frozen=True)
class RouteScore:
    sensory_score: float | None
    sensory_indicator: str
    data_availability: str
    matched_sensor_count: int
    sensor_coverage_ratio: float
    warning_message: str | None
    segment_scores: list[SegmentScore]


class SensoryScoringService:
    def score_route(
        self,
        segment_matches: list[SegmentSensorMatch],
        counts_by_sensor: dict[int, PedestrianCountRecord],
        crowd_threshold: int | None,
    ) -> RouteScore:
        # Iteration 1 formula:
        # 1. Score each covered segment from the average matched pedestrian count.
        # 2. Normalize count pressure against a central Iteration 1 threshold.
        # 3. Weight segment contributions by segment distance where available.
        # 4. Require at least 50% segment coverage before claiming High or Low.
        # 5. Lower scores are calmer; missing data never becomes a score of zero.
        threshold = DEFAULT_CROWD_THRESHOLD
        count_pressure_divisor = max(1, threshold) * 100
        segment_scores: list[SegmentScore] = []
        weighted_scores: list[tuple[float, float]] = []
        matched_sensor_ids: set[int] = set()
        congested_segments = 0
        total_segments = len(segment_matches)

        for segment_match in segment_matches:
            matched_sensor_ids.update(match.sensor.sensor_id for match in segment_match.matched_sensors)
            segment_weight = float(segment_match.distance_m or 1)
            matched_counts = [
                counts_by_sensor[match.sensor.sensor_id].total_count
                for match in segment_match.matched_sensors
                if match.sensor.sensor_id in counts_by_sensor
            ]

            if not matched_counts:
                segment_scores.append(
                    SegmentScore(
                        segment_sequence=segment_match.segment_sequence,
                        matched_sensor_count=len(segment_match.matched_sensors),
                        score=None,
                        congestion_level=None,
                        data_availability="unavailable",
                        weight=segment_weight,
                    )
                )
                continue

            average_count = sum(matched_counts) / len(matched_counts)
            segment_score = round(average_count / count_pressure_divisor, 2)
            congestion_level = self._congestion_level(average_count, threshold)
            if congestion_level == "high":
                congested_segments += 1

            weighted_scores.append((segment_score, segment_weight))
            segment_scores.append(
                SegmentScore(
                    segment_sequence=segment_match.segment_sequence,
                    matched_sensor_count=len(segment_match.matched_sensors),
                    score=segment_score,
                    congestion_level=congestion_level,
                    data_availability="available",
                    weight=segment_weight,
                )
            )

        scored_segment_count = len(weighted_scores)
        coverage_ratio = round(scored_segment_count / total_segments, 2) if total_segments else 0.0

        if not weighted_scores:
            return RouteScore(
                sensory_score=None,
                sensory_indicator="Unavailable",
                data_availability="unavailable",
                matched_sensor_count=len(matched_sensor_ids),
                sensor_coverage_ratio=coverage_ratio,
                warning_message="Pedestrian sensor data is unavailable for this route, so congestion and sensory information cannot be fully confirmed.",
                segment_scores=segment_scores,
            )

        if coverage_ratio < MINIMUM_SENSOR_COVERAGE_RATIO:
            return RouteScore(
                sensory_score=None,
                sensory_indicator="Unavailable",
                data_availability="partial",
                matched_sensor_count=len(matched_sensor_ids),
                sensor_coverage_ratio=coverage_ratio,
                warning_message="Pedestrian data coverage is too limited for this route, so congestion and sensory information cannot be fully confirmed.",
                segment_scores=segment_scores,
            )

        total_weight = sum(weight for _, weight in weighted_scores)
        weighted_average = sum(score * weight for score, weight in weighted_scores) / total_weight
        route_score = round(weighted_average + (congested_segments * 0.5), 2)
        return RouteScore(
            sensory_score=route_score,
            sensory_indicator=self._indicator(route_score),
            data_availability="available" if scored_segment_count == total_segments else "partial",
            matched_sensor_count=len(matched_sensor_ids),
            sensor_coverage_ratio=coverage_ratio,
            warning_message=None
            if scored_segment_count == total_segments
            else "Pedestrian data is partial for this route, so congestion and sensory information cannot be fully confirmed.",
            segment_scores=segment_scores,
        )

    def _congestion_level(self, average_count: float, threshold: int) -> str:
        adjusted = average_count / max(1, threshold)
        if adjusted < 80:
            return "low"
        if adjusted < 160:
            return "medium"
        return "high"

    def _indicator(self, score: float) -> str:
        if score < HIGH_SENSORY_SCORE_THRESHOLD:
            return "Low"
        return "High"
