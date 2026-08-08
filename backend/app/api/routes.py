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
    RouteCongestionResponse,
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
from app.services.route_congestion_service import RouteCongestionService
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


def get_route_congestion_service(db: Session | None = Depends(get_optional_db)) -> RouteCongestionService | None:
    return RouteCongestionService(db) if db is not None else None


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    request: RoutePlanningRequest,
    google_maps_service: GoogleMapsService = Depends(get_google_maps_service),
    pedestrian_repository: PedestrianRepository = Depends(get_pedestrian_repository),
    sensor_matching_service: SensorMatchingService = Depends(get_sensor_matching_service),
    sensory_scoring_service: SensoryScoringService = Depends(get_sensory_scoring_service),
    db: Session | None = Depends(get_optional_db),
) -> RoutePlanResponse:
    logger.info("Route planning started: path=/api/routes/plan travel_mode=%s", request.travel_mode)
    try:
        route_candidates = await google_maps_service.get_route_alternatives(request)
    except GoogleMapsServiceError as exc:
        logger.warning(
            "Route planning failed while requesting Google Maps alternatives: error_type=%s reason=%s",
            exc.__class__.__name__,
            exc,
        )
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
    recommendation = mark_recommended_route(route_responses, request.crowd_threshold)
    persist_route_plan(db, request, route_build_results)

    recommended = next((route.route_identifier for route in route_responses if route.is_recommended), None)
    logger.info("Route planning completed: path=/api/routes/plan status=200 routes=%d", len(route_responses))
    return RoutePlanResponse(
        recommended_route_identifier=recommended,
        routes=route_responses,
        preferred_crowd_threshold=request.crowd_threshold,
        threshold_message=recommendation["message"],
        all_routes_high=recommendation["all_routes_high"],
        personalised_recommendations_available=recommendation["personalised"],
    )


@router.get("/{route_id}/congestion", response_model=RouteCongestionResponse)
def get_route_congestion(
    route_id: int,
    congestion_service: RouteCongestionService | None = Depends(get_route_congestion_service),
) -> RouteCongestionResponse:
    if congestion_service is None:
        raise HTTPException(status_code=503, detail="Congestion refresh requires a configured database")

    try:
        response = congestion_service.refresh(route_id)
    except Exception as exc:
        logger.warning(
            "Congestion refresh failed: path=/api/routes/%s/congestion error_type=%s",
            route_id,
            exc.__class__.__name__,
        )
        congestion_service.db.rollback()
        raise HTTPException(status_code=503, detail="Current congestion data is temporarily unavailable") from exc

    if response is None:
        raise HTTPException(status_code=404, detail="Route was not found")
    logger.info("Congestion refresh completed: path=/api/routes/%s/congestion status=200", route_id)
    return response


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
    baseline_loader = getattr(pedestrian_repository, "get_historical_baselines", None)
    historical_baselines = baseline_loader(sorted(matched_sensor_ids)) if baseline_loader else {}
    route_score = sensory_scoring_service.score_route(
        segment_matches,
        counts_by_sensor,
        request.crowd_threshold,
        historical_baselines=historical_baselines,
    )
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
                counts_by_sensor[match.sensor.sensor_id].total_count
                / max(1.0, historical_baselines.get(match.sensor.sensor_id, DEFAULT_CROWD_THRESHOLD * 100)),
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
            pedestrian_count=score_by_sequence[segment.segment_sequence].pedestrian_count,
            threshold_exceeded=score_by_sequence[segment.segment_sequence].threshold_exceeded,
            data_source=score_by_sequence[segment.segment_sequence].data_source,
            observed_at=score_by_sequence[segment.segment_sequence].observed_at,
            freshness_status=score_by_sequence[segment.segment_sequence].freshness_status,
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
            threshold_exceeded=route_score.threshold_exceeded,
            qualifies_preference=route_score.qualifies_preference,
            data_freshness=route_score.data_freshness,
            observed_at=route_score.observed_at,
            updated_at=route_score.updated_at,
        ),
        sensor_scores=sensor_score_rows,
    )


def mark_recommended_route(
    routes: list[RouteOptionResponse],
    crowd_threshold: int = DEFAULT_CROWD_THRESHOLD,
) -> dict[str, bool | str | None]:
    valid_routes = [route for route in routes if route.sensory_score is not None]
    if not valid_routes:
        for route in routes:
            route.recommendation_explanation = "Personalised routing is unavailable because pedestrian data cannot be confirmed."
        return {
            "message": "Pedestrian data is unavailable, so personalised route recommendations cannot be generated.",
            "all_routes_high": False,
            "personalised": False,
        }

    route_order = {id(route): index for index, route in enumerate(routes)}
    qualifying_routes = [route for route in valid_routes if route.qualifies_preference]
    ranked_pool = qualifying_routes or valid_routes
    recommended = min(
        ranked_pool,
        key=lambda route: (route.sensory_score, route.estimated_travel_minutes, route_order[id(route)]),
    )
    all_routes_high = all(
        any(segment.congestion_level == "high" for segment in route.route_segments if segment.data_availability == "available")
        for route in valid_routes
    )
    fastest_minutes = min(route.estimated_travel_minutes for route in valid_routes)

    for route in routes:
        route.is_recommended = route.route_identifier == recommended.route_identifier
        high_segments = sum(segment.congestion_level == "high" for segment in route.route_segments)
        time_difference = route.estimated_travel_minutes - fastest_minutes
        if route.sensory_score is None:
            route.recommendation_explanation = "Pedestrian data is insufficient to confirm whether this route meets your preference."
        elif route.qualifies_preference:
            suffix = f" Travel time is {time_difference} minutes longer than the fastest route." if time_difference > 0 else " It is also the fastest scored route."
            route.recommendation_explanation = (
                f"Meets crowd preference level {crowd_threshold} with {high_segments} high-congestion segment"
                f"{'s' if high_segments != 1 else ''}.{suffix}"
            )
        else:
            route.recommendation_explanation = (
                f"Exceeds crowd preference level {crowd_threshold}; {high_segments} high-congestion segment"
                f"{'s' if high_segments != 1 else ''} detected."
            )

    if qualifying_routes:
        message = "One or more routes meet the selected crowd preference."
    else:
        recommended.recommendation_explanation = (
            f"Lowest calculated sensory impact available, but it still exceeds crowd preference level {crowd_threshold}."
        )
        message = "No route meets the selected crowd preference; the lowest-impact route is recommended."
    if all_routes_high:
        message = "All available routes contain high-congestion segments; the lowest-impact route is recommended."
    return {"message": message, "all_routes_high": all_routes_high, "personalised": True}


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
            preferred_crowd_threshold=request.crowd_threshold,
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
            route.route_id = route_option.route_id

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
                segment.route_segment_id = route_segment.route_segment_id
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
        for result in route_build_results:
            result.response.route_id = None
            for segment in result.response.route_segments:
                segment.route_segment_id = None
        logger.warning("Route plan persistence skipped after database error: %s", exc.__class__.__name__)
