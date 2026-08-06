from __future__ import annotations

import logging
from collections.abc import Generator
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.journey_request import JourneyRequest
from app.models.route_option import RouteOption
from app.models.route_segment import RouteSegment
from app.models.route_sensor_score import RouteSensorScore
from app.repositories.pedestrian_repository import PedestrianRepository
from app.schemas.route_planning import (
    RouteOptionResponse,
    RoutePlanResponse,
    RoutePlanningRequest,
    RouteSegmentResponse,
)
from app.services.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
    RouteCandidate,
    RouteSegmentCandidate,
)
from app.services.sensor_matching_service import SensorMatchingService, route_bounds
from app.services.sensory_scoring_service import DEFAULT_CROWD_THRESHOLD, SensoryScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/routes", tags=["routes"])


@dataclass(frozen=True)
class SegmentSensorScorePersistence:
    segment_sequence: int
    sensor_id: int
    count_source: str
    observed_at: datetime | None
    count_used: int
    score_contribution: float


@dataclass(frozen=True)
class RouteBuildResult:
    response: RouteOptionResponse
    sensor_scores: list[SegmentSensorScorePersistence]


def get_optional_db() -> Generator[Session | None, None, None]:
    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_google_maps_service() -> GoogleMapsService:
    return GoogleMapsService()


def get_sensor_matching_service() -> SensorMatchingService:
    return SensorMatchingService()


def get_sensory_scoring_service() -> SensoryScoringService:
    return SensoryScoringService()


def get_pedestrian_repository(db: Session | None = Depends(get_optional_db)) -> PedestrianRepository:
    return PedestrianRepository(db)


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    request: RoutePlanningRequest,
    google_maps_service: GoogleMapsService = Depends(get_google_maps_service),
    pedestrian_repository: PedestrianRepository = Depends(get_pedestrian_repository),
    sensor_matching_service: SensorMatchingService = Depends(get_sensor_matching_service),
    sensory_scoring_service: SensoryScoringService = Depends(get_sensory_scoring_service),
    db: Session | None = Depends(get_optional_db),
) -> RoutePlanResponse:
    try:
        route_candidates = await google_maps_service.get_route_alternatives(request)
    except GoogleMapsServiceError as exc:
        logger.warning("Route planning failed while requesting Google Maps alternatives: %s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="Route provider is unavailable") from exc

    if not route_candidates:
        raise HTTPException(status_code=502, detail="Route provider returned no route alternatives")

    route_build_results = [
        build_route_response(
            candidate=candidate,
            request=request,
            pedestrian_repository=pedestrian_repository,
            sensor_matching_service=sensor_matching_service,
            sensory_scoring_service=sensory_scoring_service,
        )
        for candidate in route_candidates
    ]
    route_responses = [result.response for result in route_build_results]
    mark_recommended_route(route_responses)
    persist_route_plan(db, request, route_build_results)

    recommended = next((route.route_identifier for route in route_responses if route.is_recommended), None)
    return RoutePlanResponse(recommended_route_identifier=recommended, routes=route_responses)


def build_route_response(
    candidate: RouteCandidate,
    request: RoutePlanningRequest,
    pedestrian_repository: PedestrianRepository,
    sensor_matching_service: SensorMatchingService,
    sensory_scoring_service: SensoryScoringService,
) -> RouteBuildResult:
    segments = candidate.segments or [
        RouteSegmentCandidate(
            segment_sequence=1,
            encoded_polyline=candidate.encoded_polyline,
            points=candidate.points,
            distance_m=None,
            duration_seconds=candidate.estimated_travel_minutes * 60,
        )
    ]

    segment_matches = []
    matched_sensor_ids: set[int] = set()
    for segment in segments:
        min_lat, max_lat, min_lng, max_lng = route_bounds(segment.points)
        sensors = pedestrian_repository.get_sensors_in_bounds(min_lat, max_lat, min_lng, max_lng)
        segment_match = sensor_matching_service.match_segment(segment, sensors)
        segment_matches.append(segment_match)
        matched_sensor_ids.update(match.sensor.sensor_id for match in segment_match.matched_sensors)

    counts_by_sensor = pedestrian_repository.get_latest_counts(sorted(matched_sensor_ids))
    route_score = sensory_scoring_service.score_route(segment_matches, counts_by_sensor, request.crowd_threshold)
    score_by_sequence = {segment_score.segment_sequence: segment_score for segment_score in route_score.segment_scores}
    sensor_score_rows = [
        SegmentSensorScorePersistence(
            segment_sequence=segment_match.segment_sequence,
            sensor_id=match.sensor.sensor_id,
            count_source=counts_by_sensor[match.sensor.sensor_id].source,
            observed_at=(
                counts_by_sensor[match.sensor.sensor_id].observed_at
                if isinstance(counts_by_sensor[match.sensor.sensor_id].observed_at, datetime)
                else datetime.combine(counts_by_sensor[match.sensor.sensor_id].observed_at, time.min, tzinfo=timezone.utc)
                if isinstance(counts_by_sensor[match.sensor.sensor_id].observed_at, date)
                else None
            ),
            count_used=counts_by_sensor[match.sensor.sensor_id].total_count,
            score_contribution=round(
                counts_by_sensor[match.sensor.sensor_id].total_count / (DEFAULT_CROWD_THRESHOLD * 100),
                2,
            ),
        )
        for segment_match in segment_matches
        for match in segment_match.matched_sensors
        if match.sensor.sensor_id in counts_by_sensor
    ]

    response_segments = [
        RouteSegmentResponse(
            segment_sequence=segment.segment_sequence,
            encoded_polyline=segment.encoded_polyline,
            distance_m=segment.distance_m,
            duration_seconds=segment.duration_seconds,
            matched_sensor_count=score_by_sequence[segment.segment_sequence].matched_sensor_count,
            congestion_level=score_by_sequence[segment.segment_sequence].congestion_level,
            sensory_score=score_by_sequence[segment.segment_sequence].score,
            data_availability=score_by_sequence[segment.segment_sequence].data_availability,
        )
        for segment in segments
    ]

    return RouteBuildResult(
        response=RouteOptionResponse(
            route_identifier=candidate.route_identifier,
            encoded_polyline=candidate.encoded_polyline,
            estimated_travel_minutes=candidate.estimated_travel_minutes,
            travel_mode=request.travel_mode,
            sensory_score=route_score.sensory_score,
            sensory_indicator=route_score.sensory_indicator,
            is_recommended=False,
            pedestrian_data_availability=route_score.data_availability,
            data_availability_status=route_score.data_availability,
            matched_sensor_count=route_score.matched_sensor_count,
            sensor_coverage_ratio=route_score.sensor_coverage_ratio,
            route_segments=response_segments,
            warning_message=route_score.warning_message,
        ),
        sensor_scores=sensor_score_rows,
    )


def mark_recommended_route(routes: list[RouteOptionResponse]) -> None:
    valid_routes = [route for route in routes if route.sensory_score is not None]
    if not valid_routes:
        return

    recommended = min(valid_routes, key=lambda route: (route.sensory_score, route.estimated_travel_minutes))
    for route in routes:
        route.is_recommended = route.route_identifier == recommended.route_identifier


def persist_route_plan(
    db: Session | None,
    request: RoutePlanningRequest,
    route_build_results: list[RouteBuildResult],
) -> None:
    if db is None:
        return

    try:
        journey_request = JourneyRequest(
            origin_latitude=request.origin_latitude,
            origin_longitude=request.origin_longitude,
            destination_latitude=request.destination_latitude,
            destination_longitude=request.destination_longitude,
            travel_mode=request.travel_mode,
            requested_at=datetime.now(timezone.utc),
        )
        db.add(journey_request)
        db.flush()

        for result in route_build_results:
            route = result.response
            route_option = RouteOption(
                journey_request_id=journey_request.journey_request_id,
                google_route_id=route.route_identifier,
                encoded_polyline=route.encoded_polyline,
                estimated_travel_minutes=route.estimated_travel_minutes,
                sensory_indicator=route.sensory_indicator,
                total_sensory_score=Decimal(str(route.sensory_score)) if route.sensory_score is not None else None,
                data_availability_status=route.pedestrian_data_availability,
                is_recommended=route.is_recommended,
                created_at=datetime.now(timezone.utc),
            )
            db.add(route_option)
            db.flush()

            persisted_segments: dict[int, RouteSegment] = {}
            for segment in route.route_segments:
                route_segment = RouteSegment(
                    route_id=route_option.route_id,
                    segment_sequence=segment.segment_sequence,
                    encoded_polyline=segment.encoded_polyline,
                    distance_m=segment.distance_m,
                    duration_seconds=segment.duration_seconds,
                    congestion_level=segment.congestion_level,
                    sensory_score=Decimal(str(segment.sensory_score)) if segment.sensory_score is not None else None,
                    data_availability_status=segment.data_availability,
                )
                db.add(route_segment)
                db.flush()
                persisted_segments[segment.segment_sequence] = route_segment

            for sensor_score in result.sensor_scores:
                route_segment = persisted_segments.get(sensor_score.segment_sequence)
                if route_segment is None:
                    continue
                db.add(
                    RouteSensorScore(
                        route_segment_id=route_segment.route_segment_id,
                        sensor_id=sensor_score.sensor_id,
                        count_source=sensor_score.count_source,
                        observed_at=sensor_score.observed_at,
                        count_used=sensor_score.count_used,
                        score_contribution=Decimal(str(sensor_score.score_contribution)),
                    )
                )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Route plan persistence skipped after database error: %s", exc.__class__.__name__)
