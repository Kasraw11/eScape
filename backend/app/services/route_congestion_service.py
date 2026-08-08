from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.route_option import RouteOption
from app.models.route_segment import RouteSegment
from app.repositories.pedestrian_repository import PedestrianRepository, SensorRecord
from app.schemas.route_planning import (
    CongestionAlternativeResponse,
    CongestionNotificationResponse,
    RouteCongestionResponse,
    RouteSegmentResponse,
)
from app.services.sensor_matching_service import MatchedSensor, SegmentSensorMatch
from app.services.sensory_scoring_service import SensoryScoringService, acceptable_congestion_score


MATERIAL_SCORE_INCREASE = 0.25


def is_meaningful_change(
    old_level: str | None,
    new_level: str | None,
    old_threshold_exceeded: bool | None,
    new_threshold_exceeded: bool | None,
    old_availability: str | None,
    new_availability: str | None,
    old_score: float | None,
    new_score: float | None,
) -> bool:
    if (old_level, new_level) in {("low", "high"), ("high", "low")}:
        return True
    if old_threshold_exceeded is not None and new_threshold_exceeded is not None and old_threshold_exceeded != new_threshold_exceeded:
        return True
    if (old_availability == "unavailable") != (new_availability == "unavailable"):
        return True
    return old_score is not None and new_score is not None and new_score - old_score >= MATERIAL_SCORE_INCREASE


class RouteCongestionService:
    def __init__(self, db: Session, scoring_service: SensoryScoringService | None = None) -> None:
        self.db = db
        self.scoring_service = scoring_service or SensoryScoringService()
        self.pedestrian_repository = PedestrianRepository(db)

    def refresh(self, route_id: int) -> RouteCongestionResponse | None:
        route = self.db.get(RouteOption, route_id)
        if route is None:
            return None

        threshold = route.journey_request.preferred_crowd_threshold
        siblings = list(route.journey_request.route_options)
        now = datetime.now(timezone.utc)
        selected_before = self._route_state(route, threshold)
        scored_routes = [(candidate, self._score_persisted_route(candidate, threshold, now)) for candidate in siblings]
        selected_score = next(score for candidate, score in scored_routes if candidate.route_id == route_id)

        changed_segment = None
        for segment, score in zip(sorted(route.route_segments, key=lambda item: item.segment_sequence), selected_score.segment_scores):
            old_score = float(segment.sensory_score) if segment.sensory_score is not None else None
            old_threshold = old_score > acceptable_congestion_score(threshold) if old_score is not None else None
            if changed_segment is None and is_meaningful_change(
                segment.congestion_level,
                score.congestion_level,
                old_threshold,
                score.threshold_exceeded,
                segment.data_availability_status,
                score.data_availability,
                old_score,
                score.score,
            ):
                changed_segment = (segment, score)

        route_meaningful = is_meaningful_change(
            selected_before["level"],
            selected_score.sensory_indicator.lower() if selected_score.sensory_indicator != "Unavailable" else None,
            selected_before["threshold"],
            selected_score.threshold_exceeded,
            selected_before["availability"],
            selected_score.data_availability,
            selected_before["score"],
            selected_score.sensory_score,
        )
        meaningful = changed_segment is not None or route_meaningful

        for candidate, score in scored_routes:
            self._persist_score(candidate, score)

        alternatives = self._rank_alternatives(route, scored_routes, threshold)
        notification = self._create_notification(route, changed_segment, selected_score, now) if meaningful else None
        self.db.commit()

        warning_messages = [selected_score.warning_message] if selected_score.warning_message else []
        if selected_score.threshold_exceeded and not alternatives:
            warning_messages.append("No lower-congestion alternative can be confirmed for the selected preference.")

        return RouteCongestionResponse(
            route_id=route.route_id,
            route_identifier=route.google_route_id or f"Route {route.route_id}",
            congestion_status=selected_score.sensory_indicator,
            sensory_score=selected_score.sensory_score,
            sensory_indicator=selected_score.sensory_indicator,
            threshold_exceeded=selected_score.threshold_exceeded,
            preferred_crowd_threshold=threshold,
            updated_at=now,
            data_freshness=selected_score.data_freshness,
            route_segments=self._segment_responses(route, selected_score),
            alternatives=alternatives,
            meaningful_change=meaningful,
            notification=notification,
            warning_messages=warning_messages,
        )

    def _score_persisted_route(self, route: RouteOption, threshold: int, now: datetime):
        segments = sorted(route.route_segments, key=lambda item: item.segment_sequence)
        sensor_ids = sorted({score.sensor_id for segment in segments for score in segment.sensor_scores})
        counts = self.pedestrian_repository.get_latest_counts(sensor_ids)
        baselines = self.pedestrian_repository.get_historical_baselines(sensor_ids)
        matches = [
            SegmentSensorMatch(
                segment_sequence=segment.segment_sequence,
                matched_sensors=[
                    MatchedSensor(
                        sensor=SensorRecord(score.sensor_id, f"Sensor {score.sensor_id}", 0, 0),
                        distance_m=0,
                        route_point_index=index,
                    )
                    for index, score in enumerate(segment.sensor_scores)
                ],
                distance_m=segment.distance_m,
            )
            for segment in segments
        ]
        return self.scoring_service.score_route(matches, counts, threshold, baselines, now)

    @staticmethod
    def _route_state(route: RouteOption, threshold: int) -> dict[str, object]:
        score = float(route.total_sensory_score) if route.total_sensory_score is not None else None
        return {
            "level": route.sensory_indicator.lower() if route.sensory_indicator != "Unavailable" else None,
            "score": score,
            "threshold": score > acceptable_congestion_score(threshold) if score is not None else None,
            "availability": route.data_availability_status,
        }

    @staticmethod
    def _persist_score(route: RouteOption, score) -> None:
        route.total_sensory_score = Decimal(str(score.sensory_score)) if score.sensory_score is not None else None
        route.sensory_indicator = score.sensory_indicator
        route.data_availability_status = score.data_availability
        for segment, segment_score in zip(sorted(route.route_segments, key=lambda item: item.segment_sequence), score.segment_scores):
            segment.congestion_level = segment_score.congestion_level
            segment.sensory_score = Decimal(str(segment_score.score)) if segment_score.score is not None else None
            segment.data_availability_status = segment_score.data_availability

    @staticmethod
    def _segment_responses(route: RouteOption, score) -> list[RouteSegmentResponse]:
        return [
            RouteSegmentResponse(
                route_segment_id=segment.route_segment_id,
                segment_sequence=segment.segment_sequence,
                encoded_polyline=segment.encoded_polyline,
                distance_m=segment.distance_m,
                duration_seconds=segment.duration_seconds,
                matched_sensor_count=segment_score.matched_sensor_count,
                congestion_level=segment_score.congestion_level,
                sensory_score=segment_score.score,
                data_availability=segment_score.data_availability,
                pedestrian_count=segment_score.pedestrian_count,
                threshold_exceeded=segment_score.threshold_exceeded,
                data_source=segment_score.data_source,
                observed_at=segment_score.observed_at,
                freshness_status=segment_score.freshness_status,
            )
            for segment, segment_score in zip(sorted(route.route_segments, key=lambda item: item.segment_sequence), score.segment_scores)
        ]

    @staticmethod
    def _rank_alternatives(
        selected: RouteOption,
        scored_routes: list[tuple[RouteOption, object]],
        threshold: int,
    ) -> list[CongestionAlternativeResponse]:
        if not next(score for route, score in scored_routes if route.route_id == selected.route_id).threshold_exceeded:
            return []
        candidates = [
            (index, route, score)
            for index, (route, score) in enumerate(scored_routes)
            if route.route_id != selected.route_id and score.sensory_score is not None
        ]
        qualifying = [item for item in candidates if item[2].qualifies_preference]
        ranked = sorted(
            qualifying or candidates,
            key=lambda item: (item[2].sensory_score, item[1].estimated_travel_minutes, item[0]),
        )
        return [
            CongestionAlternativeResponse(
                route_id=route.route_id,
                route_identifier=route.google_route_id or f"Route {route.route_id}",
                sensory_score=score.sensory_score,
                sensory_indicator=score.sensory_indicator,
                estimated_travel_minutes=route.estimated_travel_minutes,
                threshold_exceeded=bool(score.threshold_exceeded),
                recommendation_explanation=(
                    f"Meets crowd preference level {threshold} with a lower pedestrian-density score."
                    if score.qualifies_preference
                    else f"Lowest available sensory impact, but it still exceeds crowd preference level {threshold}."
                ),
            )
            for _, route, score in ranked
        ]

    def _create_notification(self, route: RouteOption, changed_segment, route_score, now: datetime):
        if changed_segment is None:
            segment = None
            segment_score = None
            level = route_score.sensory_indicator.lower()
            threshold_exceeded = bool(route_score.threshold_exceeded)
        else:
            segment, segment_score = changed_segment
            level = segment_score.congestion_level or "unavailable"
            threshold_exceeded = bool(segment_score.threshold_exceeded)

        segment_id = segment.route_segment_id if segment is not None else None
        message = (
            f"Segment {segment.segment_sequence} is now {level} congestion."
            if segment is not None
            else f"The selected route is now {level} congestion."
        )
        if threshold_exceeded:
            message += " Your crowd preference is exceeded; review available alternatives."

        existing = self.db.scalar(
            select(Alert).where(
                Alert.route_id == route.route_id,
                Alert.route_segment_id == segment_id,
                Alert.alert_type == "congestion_change",
                Alert.status == "active",
                Alert.message == message,
            )
        )
        if existing is not None:
            return None

        active_alerts = self.db.scalars(
            select(Alert).where(
                Alert.route_id == route.route_id,
                Alert.route_segment_id == segment_id,
                Alert.alert_type == "congestion_change",
                Alert.status == "active",
            )
        ).all()
        for alert in active_alerts:
            alert.status = "superseded"

        self.db.add(
            Alert(
                route_id=route.route_id,
                route_segment_id=segment_id,
                sensor_id=None,
                alert_type="congestion_change",
                severity="high" if threshold_exceeded else "info",
                message=message,
                status="active",
                created_at=now,
            )
        )
        return CongestionNotificationResponse(
            change_key=f"{route.route_id}:{segment_id or 'route'}:{level}:{int(threshold_exceeded)}:{now.isoformat()}",
            route_id=route.route_id,
            route_segment_id=segment_id,
            segment_sequence=segment.segment_sequence if segment is not None else None,
            congestion_level=level,
            threshold_exceeded=threshold_exceeded,
            updated_at=now,
            message=message,
        )
