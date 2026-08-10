from __future__ import annotations

import logging
import time as perf_time

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

from app.models.transport_stop import RouteTransportStop

from app.services.transport_stop_service import (
    find_transport_stops_near_route,
)

from app.schemas.route_planning import (
    MatchedSensorResponse,
    RouteOptionResponse,
    RoutePlanResponse,
    RoutePlanningRequest,
    RouteSegmentResponse,
    TransportStopResponse,
)

# Generic routing models.
from app.services.routing_models import (
    RouteCandidate,
    RouteSegmentCandidate,
)

# Generic routing interface.
from app.services.routing_service import (
    RoutingService,
    RoutingServiceError,
)

# Current MVP routing provider.
from app.services.osrm_service import OSRMService

from app.services.sensor_matching_service import (
    MatchedSensor,
    SegmentSensorMatch,
    SensorMatchingService,
    route_bounds,
)

from app.services.sensory_scoring_service import (
    DEFAULT_HISTORICAL_BASELINE_COUNT,
    SensoryScoringService,
    acceptable_congestion_score,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/routes",
    tags=["routes"],
)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SegmentSensorScorePersistence:
    """
    Stores sensor-scoring information that will later
    be written to the database.
    """

    segment_sequence: int
    sensor_id: int
    count_source: str
    observed_at: datetime | None
    count_used: int
    score_contribution: float


@dataclass(frozen=True)
class RouteBuildResult:
    """
    Contains the frontend route response together with
    the information needed for database persistence.
    """

    response: RouteOptionResponse

    sensor_scores: list[
        SegmentSensorScorePersistence
    ]

    # Keep the original provider-independent route geometry.
    # This is used when matching nearby public transport stops.
    candidate: RouteCandidate


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_optional_db() -> Generator[Session | None, None, None]:
    """
    Creates a database session when the database is available.

    Route planning can still work without a database;
    persistence is simply skipped.
    """

    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_routing_service() -> RoutingService:
    """
    Returns the routing provider used by the backend.

    The current MVP uses OSRM for walking routes.
    """

    return OSRMService()


def get_sensor_matching_service() -> SensorMatchingService:
    """
    Creates the service used to match route segments
    with nearby pedestrian sensors.
    """

    return SensorMatchingService()


def get_sensory_scoring_service() -> SensoryScoringService:
    """
    Creates the service that calculates sensory /
    congestion scores for routes.
    """

    return SensoryScoringService()


def get_pedestrian_repository(
    db: Session | None = Depends(get_optional_db),
) -> PedestrianRepository:
    """
    Provides pedestrian sensor and pedestrian-count data.
    """

    return PedestrianRepository(db)


# ---------------------------------------------------------------------------
# Route planning
# ---------------------------------------------------------------------------

@router.post(
    "/plan",
    response_model=RoutePlanResponse,
)
async def plan_route(
    request: RoutePlanningRequest,

    routing_service: RoutingService = Depends(
        get_routing_service
    ),

    pedestrian_repository: PedestrianRepository = Depends(
        get_pedestrian_repository
    ),

    sensor_matching_service: SensorMatchingService = Depends(
        get_sensor_matching_service
    ),

    sensory_scoring_service: SensoryScoringService = Depends(
        get_sensory_scoring_service
    ),

    db: Session | None = Depends(get_optional_db),

) -> RoutePlanResponse:
    """
    Plans possible journeys between the origin
    and destination.

    Flow:

        Origin + destination
                ↓
        OSRM walking routes
                ↓
        Pedestrian sensor matching
                ↓
        Latest pedestrian counts
                ↓
        Sensory scoring
                ↓
        Calmer-route recommendation
                ↓
        Frontend response
    """
    request_start = perf_time.perf_counter()

    logger.info(
        "Route planning started: "
        "path=/api/routes/plan"
    )

    # --------------------------------------------------------------
    # 1. Request route alternatives from OSRM.
    # --------------------------------------------------------------

    # --------------------------------------------------------------
    # 1. Request route alternatives from OSRM.
    # --------------------------------------------------------------

    try:
        osrm_start = perf_time.perf_counter()

        route_candidates = (
            await routing_service.get_route_alternatives(
                request
            )
        )

        print(
            "PERFORMANCE OSRM:",
            round(
                perf_time.perf_counter() - osrm_start,
                2,
            ),
            "seconds",
        )

    except RoutingServiceError as exc:
        logger.warning(
            "Route provider failed: "
            "path=/api/routes/plan "
            "error_type=%s reason=%s",
            exc.__class__.__name__,
            exc,
        )

        raise HTTPException(
            status_code=502,
            detail="Route provider is unavailable",
        ) from exc

    # --------------------------------------------------------------
    # 2. Match sensors and calculate sensory information.
    # --------------------------------------------------------------

    route_build_results: list[RouteBuildResult] = []

    for candidate in route_candidates:
        try:
            route_start = perf_time.perf_counter()

            result = build_route_response(
                candidate=candidate,
                request=request,
                pedestrian_repository=pedestrian_repository,
                sensor_matching_service=sensor_matching_service,
                sensory_scoring_service=sensory_scoring_service,
            )

            print(
                "PERFORMANCE sensory route",
                candidate.route_identifier,
                ":",
                round(
                    perf_time.perf_counter() - route_start,
                    2,
                ),
                "seconds",
            )

            route_build_results.append(
                result
            )

        except Exception as exc:
            logger.exception(
                "Sensory route processing failed: "
                "route=%s error_type=%s",
                candidate.route_identifier,
                exc.__class__.__name__,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Unable to calculate sensory "
                    "information for the route."
                ),
            ) from exc

    # --------------------------------------------------------------
    # 3. Extract route responses.
    # --------------------------------------------------------------

    route_responses = [
        result.response
        for result in route_build_results
    ]

    # --------------------------------------------------------------
    # 4. Recommend the calmer route.
    # --------------------------------------------------------------
    recommendation_start = perf_time.perf_counter()

    recommendation = mark_recommended_route(
        routes=route_responses,
        crowd_threshold=request.crowd_threshold,
    )

    recommended_identifier = next(
        (
            route.route_identifier
            for route in route_responses
            if route.is_recommended
        ),
        None,
    )

    # --------------------------------------------------------------
    # 5. Persist route information if DB is available.
    # --------------------------------------------------------------

    persist_start = perf_time.perf_counter()

    persist_route_plan(
        db=db,
        request=request,
        route_build_results=route_build_results,
    )

    print(
        "PERFORMANCE persistence:",
        round(
            perf_time.perf_counter() - persist_start,
            2,
        ),
        "seconds",
    )

    # --------------------------------------------------------------
    # 6. Log completion.
    # --------------------------------------------------------------

    logger.info(
        "Route planning completed: "
        "path=/api/routes/plan "
        "status=200 routes=%d "
        "recommended=%s",
        len(route_responses),
        recommended_identifier,
    )

    print(
        "PERFORMANCE TOTAL REQUEST:",
        round(
            perf_time.perf_counter() - request_start,
            2,
        ),
        "seconds",
    )

    # --------------------------------------------------------------
    # 7. Return result.
    # --------------------------------------------------------------

    return RoutePlanResponse(
        recommended_route_identifier=(
            recommended_identifier
        ),

        routes=route_responses,

        preferred_crowd_threshold=(
            request.crowd_threshold
        ),

        threshold_message=(
            recommendation["message"]
        ),

        all_routes_high=bool(
            recommendation["all_routes_high"]
        ),

        personalised_recommendations_available=bool(
            recommendation["personalised"]
        ),
        
    )

# ---------------------------------------------------------------------------
# Current route congestion
# ---------------------------------------------------------------------------


@router.get("/{route_identifier}/congestion")
def get_route_congestion(
    route_identifier: str,

    pedestrian_repository: PedestrianRepository = Depends(
        get_pedestrian_repository
    ),

    sensory_scoring_service: SensoryScoringService = Depends(
        get_sensory_scoring_service
    ),

    db: Session | None = Depends(
        get_optional_db
    ),
):
    """
    Refresh congestion information for an active route.

    Uses the sensors that were matched when the route
    was originally planned, fetches the latest pedestrian
    counts, and recalculates the sensory score.
    """

    if db is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live congestion information is unavailable "
                "because the database is not connected."
            ),
        )

    # --------------------------------------------------------------
    # 1. Find the latest persisted version of this route.
    # --------------------------------------------------------------

    route_option = (
        db.query(RouteOption)
        .filter(
            RouteOption.google_route_id
            == route_identifier
        )
        .order_by(
            RouteOption.created_at.desc()
        )
        .first()
    )

    if route_option is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Route '{route_identifier}' "
                "could not be found."
            ),
        )

    # --------------------------------------------------------------
    # 2. Load the original journey and user crowd preference.
    # --------------------------------------------------------------

    journey_request = (
        db.query(JourneyRequest)
        .filter(
            JourneyRequest.journey_request_id
            == route_option.journey_request_id
        )
        .first()
    )

    if journey_request is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "The journey associated with this route "
                "could not be found."
            ),
        )

    crowd_threshold = (
        journey_request.preferred_crowd_threshold
    )

    # --------------------------------------------------------------
    # 3. Load persisted route segments.
    # --------------------------------------------------------------

    persisted_segments = (
        db.query(RouteSegment)
        .filter(
            RouteSegment.route_id
            == route_option.route_id
        )
        .order_by(
            RouteSegment.segment_sequence
        )
        .all()
    )

    if not persisted_segments:
        raise HTTPException(
            status_code=404,
            detail=(
                "No persisted route segments were found "
                "for this route."
            ),
        )

    # --------------------------------------------------------------
    # 4. Load the sensors originally matched to each segment.
    # --------------------------------------------------------------

    segment_sensor_rows: dict[
        int,
        list[RouteSensorScore],
    ] = {}

    all_sensor_ids: set[int] = set()

    for segment in persisted_segments:
        sensor_rows = (
            db.query(RouteSensorScore)
            .filter(
                RouteSensorScore.route_segment_id
                == segment.route_segment_id
            )
            .all()
        )

        segment_sensor_rows[
            segment.segment_sequence
        ] = sensor_rows

        all_sensor_ids.update(
            row.sensor_id
            for row in sensor_rows
        )

    sensor_ids = sorted(
        all_sensor_ids
    )

    sensor_records = (
        pedestrian_repository.get_sensors_by_ids(
            sensor_ids
        )
    )

    # --------------------------------------------------------------
    # 5. Reconstruct SegmentSensorMatch objects.
    # --------------------------------------------------------------

    segment_matches: list[
        SegmentSensorMatch
    ] = []

    for segment in persisted_segments:
        matched_sensors = []

        sensor_rows = (
            segment_sensor_rows.get(
                segment.segment_sequence,
                [],
            )
        )

        for sensor_row in sensor_rows:
            sensor = sensor_records.get(
                sensor_row.sensor_id
            )

            if sensor is None:
                continue

            matched_sensors.append(
                MatchedSensor(
                    sensor=sensor,
                    distance_m=0.0,
                    route_point_index=0,
                )
            )

        segment_matches.append(
            SegmentSensorMatch(
                segment_sequence=(
                    segment.segment_sequence
                ),
                matched_sensors=(
                    matched_sensors
                ),
                distance_m=(
                    segment.distance_m
                ),
            )
        )

    # --------------------------------------------------------------
    # 6. Fetch the latest pedestrian information.
    # --------------------------------------------------------------

    latest_counts = (
        pedestrian_repository.get_latest_counts(
            sensor_ids
        )
    )

    historical_baselines = (
        pedestrian_repository.get_historical_baselines(
            sensor_ids
        )
    )

    # --------------------------------------------------------------
    # 7. Remember previous route state.
    # --------------------------------------------------------------

    previous_score = (
        float(
            route_option.total_sensory_score
        )
        if route_option.total_sensory_score
        is not None
        else None
    )

    previous_indicator = (
        route_option.sensory_indicator
        or "Unavailable"
    )

    preference_limit = (
        acceptable_congestion_score(
            crowd_threshold
        )
    )

    previous_threshold_exceeded = (
        previous_score > preference_limit
        if previous_score is not None
        else None
    )

    # --------------------------------------------------------------
    # 8. Recalculate congestion using the normal scoring service.
    # --------------------------------------------------------------

    refreshed_score = (
        sensory_scoring_service.score_route(
            segment_matches=segment_matches,
            counts_by_sensor=latest_counts,
            crowd_threshold=crowd_threshold,
            historical_baselines=historical_baselines,
        )
    )

    # --------------------------------------------------------------
    # 9. Detect meaningful changes.
    # --------------------------------------------------------------

    level_changed = (
        refreshed_score.sensory_indicator
        != previous_indicator
    )

    threshold_changed = (
        refreshed_score.threshold_exceeded
        != previous_threshold_exceeded
    )

    newly_exceeded = (
        refreshed_score.threshold_exceeded
        is True
        and previous_threshold_exceeded
        is not True
    )

    returned_to_preference = (
        refreshed_score.threshold_exceeded
        is False
        and previous_threshold_exceeded
        is True
    )

    meaningful_change = bool(
        level_changed
        or threshold_changed
    )

    # --------------------------------------------------------------
    # 10. Create notification.
    # --------------------------------------------------------------

    notification = None

    if meaningful_change:

        if newly_exceeded:
            message = (
                "Crowding on your selected route has "
                "increased above your crowd preference."
            )

        elif returned_to_preference:
            message = (
                "Crowding on your selected route has "
                "decreased and is now within your "
                "crowd preference."
            )

        elif level_changed:
            message = (
                f"Crowd conditions changed from "
                f"{previous_indicator} to "
                f"{refreshed_score.sensory_indicator}."
            )

        else:
            message = (
                "Crowd conditions on your selected "
                "route have changed."
            )

        notification = {
            "change_key": (
                f"{route_option.route_id}-"
                f"{refreshed_score.sensory_indicator}-"
                f"{refreshed_score.threshold_exceeded}-"
                f"{refreshed_score.updated_at.isoformat()}"
            ),

            "route_identifier":
                route_identifier,

            "congestion_level":
                refreshed_score.sensory_indicator,

            "threshold_exceeded":
                refreshed_score.threshold_exceeded,

            "sensory_score":
                refreshed_score.sensory_score,

            "data_freshness":
                refreshed_score.data_freshness,

            "message":
                message,

            "updated_at":
                refreshed_score.updated_at.isoformat(),
        }

    # --------------------------------------------------------------
    # 11. Build refreshed segment responses.
    # --------------------------------------------------------------

    score_by_sequence = {
        score.segment_sequence: score
        for score
        in refreshed_score.segment_scores
    }

    segment_responses = []

    for segment in persisted_segments:
        score = score_by_sequence.get(
            segment.segment_sequence
        )

        if score is None:
            continue

        segment_responses.append(
            {
                "route_segment_id":
                    segment.route_segment_id,

                "segment_sequence":
                    segment.segment_sequence,

                "encoded_polyline":
                    segment.encoded_polyline,

                "distance_m":
                    segment.distance_m,

                "duration_seconds":
                    segment.duration_seconds,

                "congestion_level":
                    score.congestion_level,

                "sensory_score":
                    score.score,

                "pedestrian_count":
                    score.pedestrian_count,

                "threshold_exceeded":
                    score.threshold_exceeded,

                "data_availability":
                    score.data_availability,

                "data_source":
                    score.data_source,

                "observed_at":
                    (
                        score.observed_at.isoformat()
                        if score.observed_at
                        else None
                    ),

                "freshness_status":
                    score.freshness_status,
            }
        )

    # --------------------------------------------------------------
    # 12. Persist the refreshed congestion state.
    # --------------------------------------------------------------

    route_option.total_sensory_score = (
        Decimal(
            str(
                refreshed_score.sensory_score
            )
        )
        if refreshed_score.sensory_score
        is not None
        else None
    )

    route_option.sensory_indicator = (
        refreshed_score.sensory_indicator
    )

    route_option.data_availability_status = (
        refreshed_score.data_availability
    )

    for segment in persisted_segments:
        score = score_by_sequence.get(
            segment.segment_sequence
        )

        if score is None:
            continue

        segment.congestion_level = (
            score.congestion_level
        )

        segment.sensory_score = (
            Decimal(
                str(score.score)
            )
            if score.score is not None
            else None
        )

        segment.data_availability_status = (
            score.data_availability
        )

    try:
        db.commit()

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unable to persist refreshed "
            "route congestion: %s",
            exc,
        )

    # --------------------------------------------------------------
    # 13. Return current live congestion.
    # --------------------------------------------------------------

    return {
        "route_id":
            route_option.route_id,

        "route_identifier":
            route_identifier,

        "sensory_score":
            refreshed_score.sensory_score,

        "sensory_indicator":
            refreshed_score.sensory_indicator,

        "threshold_exceeded":
            refreshed_score.threshold_exceeded,

        "qualifies_preference":
            refreshed_score.qualifies_preference,

        "preferred_crowd_threshold":
            crowd_threshold,

        "data_freshness":
            refreshed_score.data_freshness,

        "sensor_coverage_ratio":
            refreshed_score.sensor_coverage_ratio,

        "matched_sensor_count":
            refreshed_score.matched_sensor_count,

        "observed_at":
            (
                refreshed_score.observed_at.isoformat()
                if refreshed_score.observed_at
                else None
            ),

        "updated_at":
            refreshed_score.updated_at.isoformat(),

        "route_segments":
            segment_responses,

        "meaningful_change":
            meaningful_change,

        "notification":
            notification,
    }

@router.get("/{route_identifier}/alternative")
def get_calmer_alternative(
    route_identifier: str,

    pedestrian_repository: PedestrianRepository = Depends(
        get_pedestrian_repository
    ),

    sensory_scoring_service: SensoryScoringService = Depends(
        get_sensory_scoring_service
    ),

    db: Session | None = Depends(
        get_optional_db
    ),
):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Alternative routes are unavailable because "
                "the database is not connected."
            ),
        )

    # --------------------------------------------------------------
    # 1. Find the current route.
    # --------------------------------------------------------------

    current_route = (
        db.query(RouteOption)
        .filter(
            RouteOption.google_route_id
            == route_identifier
        )
        .order_by(
            RouteOption.created_at.desc()
        )
        .first()
    )

    if current_route is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Route '{route_identifier}' "
                "could not be found."
            ),
        )

    # --------------------------------------------------------------
    # 2. Load journey + user's crowd preference.
    # --------------------------------------------------------------

    journey_request = (
        db.query(JourneyRequest)
        .filter(
            JourneyRequest.journey_request_id
            == current_route.journey_request_id
        )
        .first()
    )

    if journey_request is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "The journey associated with this route "
                "could not be found."
            ),
        )

    crowd_threshold = (
        journey_request.preferred_crowd_threshold
    )

    # --------------------------------------------------------------
    # Helper: calculate LIVE score for one saved route.
    # --------------------------------------------------------------

    def calculate_live_score(
        route_option: RouteOption,
    ):
        persisted_segments = (
            db.query(RouteSegment)
            .filter(
                RouteSegment.route_id
                == route_option.route_id
            )
            .order_by(
                RouteSegment.segment_sequence
            )
            .all()
        )

        if not persisted_segments:
            return None

        segment_sensor_rows: dict[
            int,
            list[RouteSensorScore],
        ] = {}

        all_sensor_ids: set[int] = set()

        for segment in persisted_segments:
            sensor_rows = (
                db.query(RouteSensorScore)
                .filter(
                    RouteSensorScore.route_segment_id
                    == segment.route_segment_id
                )
                .all()
            )

            segment_sensor_rows[
                segment.segment_sequence
            ] = sensor_rows

            all_sensor_ids.update(
                row.sensor_id
                for row in sensor_rows
            )

        sensor_ids = sorted(
            all_sensor_ids
        )

        sensor_records = (
            pedestrian_repository.get_sensors_by_ids(
                sensor_ids
            )
        )

        segment_matches: list[
            SegmentSensorMatch
        ] = []

        for segment in persisted_segments:
            matched_sensors = []

            sensor_rows = (
                segment_sensor_rows.get(
                    segment.segment_sequence,
                    [],
                )
            )

            for sensor_row in sensor_rows:
                sensor = sensor_records.get(
                    sensor_row.sensor_id
                )

                if sensor is None:
                    continue

                matched_sensors.append(
                    MatchedSensor(
                        sensor=sensor,
                        distance_m=0.0,
                        route_point_index=0,
                    )
                )

            segment_matches.append(
                SegmentSensorMatch(
                    segment_sequence=(
                        segment.segment_sequence
                    ),

                    matched_sensors=(
                        matched_sensors
                    ),

                    distance_m=(
                        segment.distance_m
                    ),
                )
            )

        latest_counts = (
            pedestrian_repository.get_latest_counts(
                sensor_ids
            )
        )

        historical_baselines = (
            pedestrian_repository.get_historical_baselines(
                sensor_ids
            )
        )

        return (
            sensory_scoring_service.score_route(
                segment_matches=
                    segment_matches,

                counts_by_sensor=
                    latest_counts,

                crowd_threshold=
                    crowd_threshold,

                historical_baselines=
                    historical_baselines,
            )
        )

    # --------------------------------------------------------------
    # 3. Calculate LIVE score for current route.
    # --------------------------------------------------------------

    current_live_score = (
        calculate_live_score(
            current_route
        )
    )

    if (
        current_live_score is None
        or current_live_score.sensory_score
        is None
    ):
        return {
            "alternative_available": False,
            "alternative": None,
            "message": (
                "Current route does not have enough "
                "live pedestrian data for comparison."
            ),
        }

    current_score = float(
        current_live_score.sensory_score
    )

    # --------------------------------------------------------------
    # 4. Find other routes from the SAME journey.
    # --------------------------------------------------------------

    alternative_routes = (
        db.query(RouteOption)
        .filter(
            RouteOption.journey_request_id
            == current_route.journey_request_id,

            RouteOption.route_id
            != current_route.route_id,
        )
        .all()
    )

    if not alternative_routes:
        return {
            "alternative_available": False,
            "alternative": None,
            "message": (
                "No alternative route is available "
                "for this journey."
            ),
        }

    # --------------------------------------------------------------
    # 5. Re-score each alternative using LIVE data.
    # --------------------------------------------------------------

    live_alternatives = []

    for route in alternative_routes:
        live_score = (
            calculate_live_score(
                route
            )
        )

        if (
            live_score is None
            or live_score.sensory_score
            is None
        ):
            continue

        live_alternatives.append(
            {
                "route": route,
                "score": live_score,
            }
        )

    if not live_alternatives:
        return {
            "alternative_available": False,
            "alternative": None,
            "message": (
                "No alternative route has enough "
                "live pedestrian data."
            ),
        }

    # --------------------------------------------------------------
    # 6. Only keep routes calmer than current route.
    # --------------------------------------------------------------

    calmer_alternatives = [
        item
        for item in live_alternatives
        if (
            float(
                item["score"].sensory_score
            )
            < current_score
        )
    ]

    if not calmer_alternatives:
        return {
            "alternative_available": False,

            "alternative": None,

            "current_route": {
                "route_identifier":
                    current_route.google_route_id,

                "sensory_score":
                    current_live_score.sensory_score,

                "sensory_indicator":
                    current_live_score.sensory_indicator,
            },

            "message": (
                "No calmer route is currently available."
            ),
        }

    # --------------------------------------------------------------
    # 7. Pick best calmer alternative.
    # --------------------------------------------------------------

    best = min(
        calmer_alternatives,
        key=lambda item: (
            float(
                item["score"].sensory_score
            ),

            item[
                "route"
            ].estimated_travel_minutes,
        ),
    )

    best_route = (
        best["route"]
    )

    best_score = (
        best["score"]
    )

    # --------------------------------------------------------------
    # 8. Return comparison.
    # --------------------------------------------------------------

    return {
        "alternative_available": True,

        "message": (
            "A calmer route is currently available."
        ),

        "current_route": {
            "route_id":
                current_route.route_id,

            "route_identifier":
                current_route.google_route_id,

            "sensory_score":
                current_live_score.sensory_score,

            "sensory_indicator":
                current_live_score.sensory_indicator,

            "threshold_exceeded":
                current_live_score.threshold_exceeded,
        },

        "alternative": {
            "route_id":
                best_route.route_id,

            "route_identifier":
                best_route.google_route_id,

            "sensory_score":
                best_score.sensory_score,

            "sensory_indicator":
                best_score.sensory_indicator,

            "threshold_exceeded":
                best_score.threshold_exceeded,

            "qualifies_preference":
                best_score.qualifies_preference,

            "data_freshness":
                best_score.data_freshness,

            "sensor_coverage_ratio":
                best_score.sensor_coverage_ratio,

            "estimated_travel_minutes":
                best_route.estimated_travel_minutes,

            "is_recommended":
                best_route.is_recommended,
        },
    }

# ---------------------------------------------------------------------------
# Route + sensory scoring
# ---------------------------------------------------------------------------
def build_route_response(
    candidate: RouteCandidate,
    request: RoutePlanningRequest,
    pedestrian_repository: PedestrianRepository,
    sensor_matching_service: SensorMatchingService,
    sensory_scoring_service: SensoryScoringService,
) -> RouteBuildResult:
    """
    Converts one routing-provider result into
    an eScape sensory-aware route.
    """

    # --------------------------------------------------------------
    # 1. Obtain route segments.
    # --------------------------------------------------------------

    segments = (
        candidate.segments
        or [
            RouteSegmentCandidate(
                segment_sequence=1,

                encoded_polyline=(
                    candidate.encoded_polyline
                ),

                points=(
                    candidate.points
                ),

                distance_m=None,

                duration_seconds=(
                    candidate
                    .estimated_travel_minutes
                    * 60
                ),
            )
        ]
    )


    # --------------------------------------------------------------
    # 2. Match pedestrian sensors to route segments.
    # --------------------------------------------------------------

    segment_matches: list[
        SegmentSensorMatch
    ] = []

    matched_sensor_ids: set[int] = (
        set()
    )


    for segment in segments:
        min_lat, max_lat, min_lng, max_lng = (
            route_bounds(
                segment.points
            )
        )


        sensors = (
            pedestrian_repository
            .get_sensors_in_bounds(
                min_lat,
                max_lat,
                min_lng,
                max_lng,
            )
        )


        segment_match = (
            sensor_matching_service
            .match_segment(
                segment,
                sensors,
            )
        )


        segment_matches.append(
            segment_match
        )


        matched_sensor_ids.update(
            match.sensor.sensor_id
            for match
            in segment_match.matched_sensors
        )


    # --------------------------------------------------------------
    # 3. Load latest pedestrian counts.
    # --------------------------------------------------------------

    counts_by_sensor = (
        pedestrian_repository
        .get_latest_counts(
            sorted(
                matched_sensor_ids
            )
        )
    )


    # --------------------------------------------------------------
    # 4. Load historical sensor baselines.
    # --------------------------------------------------------------

    baseline_loader = getattr(
        pedestrian_repository,
        "get_historical_baselines",
        None,
    )


    historical_baselines = (
        baseline_loader(
            sorted(
                matched_sensor_ids
            )
        )
        if baseline_loader
        else {}
    )


    # --------------------------------------------------------------
    # 5. Calculate sensory score.
    # --------------------------------------------------------------

    route_score = (
        sensory_scoring_service
        .score_route(
            segment_matches,

            counts_by_sensor,

            request.crowd_threshold,

            historical_baselines=(
                historical_baselines
            ),
        )
    )


    score_by_sequence = {
        segment_score.segment_sequence:
            segment_score

        for segment_score
        in route_score.segment_scores
    }


    # --------------------------------------------------------------
    # 6. Build sensor-match lookup.
    #
    # This lets us attach actual sensor locations
    # to the matching route segment.
    # --------------------------------------------------------------

    segment_match_by_sequence = {
        segment_match.segment_sequence:
            segment_match

        for segment_match
        in segment_matches
    }


    # --------------------------------------------------------------
    # 7. Prepare sensor scoring information
    #    for database persistence.
    # --------------------------------------------------------------

    sensor_score_rows = [
        SegmentSensorScorePersistence(
            segment_sequence=(
                segment_match
                .segment_sequence
            ),

            sensor_id=(
                match.sensor.sensor_id
            ),

            count_source=(
                counts_by_sensor[
                    match.sensor.sensor_id
                ].source
            ),

            observed_at=(
                counts_by_sensor[
                    match.sensor.sensor_id
                ].observed_at

                if isinstance(
                    counts_by_sensor[
                        match.sensor.sensor_id
                    ].observed_at,
                    datetime,
                )

                else datetime.combine(
                    counts_by_sensor[
                        match.sensor.sensor_id
                    ].observed_at,

                    time.min,

                    tzinfo=timezone.utc,
                )

                if isinstance(
                    counts_by_sensor[
                        match.sensor.sensor_id
                    ].observed_at,
                    date,
                )

                else None
            ),

            count_used=(
                counts_by_sensor[
                    match.sensor.sensor_id
                ].total_count
            ),

            score_contribution=round(
                counts_by_sensor[
                    match.sensor.sensor_id
                ].total_count

                / max(
                    1.0,

                    historical_baselines.get(
                        match.sensor.sensor_id,

                        DEFAULT_HISTORICAL_BASELINE_COUNT,
                    ),
                ),

                2,
            ),
        )

        for segment_match
        in segment_matches

        for match
        in segment_match.matched_sensors

        if (
            match.sensor.sensor_id
            in counts_by_sensor
        )
    ]


    # --------------------------------------------------------------
    # 8. Build route segment responses.
    # --------------------------------------------------------------

    response_segments = []


    for segment in segments:
        segment_score = (
            score_by_sequence.get(
                segment.segment_sequence
            )
        )


        if segment_score is None:
            continue


        segment_match = (
            segment_match_by_sequence.get(
                segment.segment_sequence
            )
        )


        matched_sensors = []


        if segment_match:
            for match in (
                segment_match
                .matched_sensors
            ):
                sensor_id = (
                    match.sensor.sensor_id
                )


                count_record = (
                    counts_by_sensor.get(
                        sensor_id
                    )
                )


                matched_sensors.append(
                    MatchedSensorResponse(
                        sensor_id=(
                            sensor_id
                        ),

                        sensor_name=(
                            match
                            .sensor
                            .sensor_name
                        ),

                        latitude=float(
                            match
                            .sensor
                            .latitude
                        ),

                        longitude=float(
                            match
                            .sensor
                            .longitude
                        ),

                        pedestrian_count=(
                            count_record
                            .total_count
                            if count_record
                            else None
                        ),

                        # For the MVP, the sensor
                        # inherits the congestion
                        # classification of the
                        # route segment it affects.
                        congestion_level=(
                            segment_score
                            .congestion_level
                        ),
                    )
                )


        response_segments.append(
            RouteSegmentResponse(
                segment_sequence=(
                    segment
                    .segment_sequence
                ),

                encoded_polyline=(
                    segment
                    .encoded_polyline
                ),

                points=(
                    segment.points
                ),

                distance_m=(
                    segment.distance_m
                ),

                duration_seconds=(
                    segment.duration_seconds
                ),

                matched_sensor_count=(
                    segment_score
                    .matched_sensor_count
                ),

                matched_sensors=(
                    matched_sensors
                ),

                congestion_level=(
                    segment_score
                    .congestion_level
                ),

                sensory_score=(
                    segment_score.score
                ),

                data_availability=(
                    segment_score
                    .data_availability
                ),

                pedestrian_count=(
                    segment_score
                    .pedestrian_count
                ),

                threshold_exceeded=bool(
                    segment_score
                    .threshold_exceeded
                ),

                data_source=(
                    segment_score
                    .data_source
                ),

                observed_at=(
                    segment_score
                    .observed_at
                ),

                freshness_status=(
                    segment_score
                    .freshness_status
                ),
            )
        )


    # --------------------------------------------------------------
    # 9. Build complete route response.
    # --------------------------------------------------------------

    return RouteBuildResult(
        response=RouteOptionResponse(
            route_identifier=(
                candidate.route_identifier
            ),

            points=(
                candidate.points
            ),

            encoded_polyline=(
                candidate.encoded_polyline
            ),

            estimated_travel_minutes=(
                candidate
                .estimated_travel_minutes
            ),

            travel_mode=(
                request.travel_mode
            ),

            sensory_score=(
                route_score
                .sensory_score
            ),

            sensory_indicator=(
                route_score
                .sensory_indicator
            ),

            is_recommended=False,

            pedestrian_data_availability=(
                route_score
                .data_availability
            ),

            data_availability_status=(
                route_score
                .data_availability
            ),

            matched_sensor_count=(
                route_score
                .matched_sensor_count
            ),

            sensor_coverage_ratio=(
                route_score
                .sensor_coverage_ratio
            ),

            route_segments=(
                response_segments
            ),

            warning_message=(
                route_score
                .warning_message
            ),

            threshold_exceeded=bool(
                route_score
                .threshold_exceeded
            ),

            qualifies_preference=(
                route_score
                .qualifies_preference
            ),

            data_freshness=(
                route_score
                .data_freshness
            ),

            observed_at=(
                route_score
                .observed_at
            ),

            updated_at=(
                route_score
                .updated_at
            ),
        ),

        sensor_scores=(
            sensor_score_rows
        ),

        candidate=candidate,
    )


# ---------------------------------------------------------------------------
# Route recommendation
# ---------------------------------------------------------------------------

def mark_recommended_route(
    routes: list[RouteOptionResponse],
    crowd_threshold: int,
) -> dict[str, bool | str | None]:
    """
    Choose the best sensory-aware route.

    Recommendation priority:

    1. Better pedestrian-data reliability
    2. Meets the user's crowd preference
    3. Lower sensory score
    4. Higher sensor coverage
    5. Shorter travel time
    6. Original OSRM ordering
    """

    # Only routes with a calculated sensory score
    # can be considered for personalised recommendation.
    valid_routes = [
        route
        for route in routes
        if route.sensory_score is not None
    ]

    # --------------------------------------------------------------
    # No usable sensory information.
    # --------------------------------------------------------------

    if not valid_routes:
        for route in routes:
            route.recommendation_explanation = (
                "Personalised routing is unavailable because "
                "pedestrian data cannot be confirmed."
            )

        return {
            "message": (
                "Pedestrian data is unavailable, so "
                "a personalised calmer route cannot be confirmed."
            ),
            "all_routes_high": False,
            "personalised": False,
        }

    # Preserve original OSRM route ordering
    # as the final tie-breaker.
    route_order = {
        id(route): index
        for index, route in enumerate(routes)
    }

    # --------------------------------------------------------------
    # Data reliability ranking.
    # --------------------------------------------------------------

    def freshness_rank(
        route: RouteOptionResponse,
    ) -> int:
        """
        Lower number = fresher pedestrian data.
        """

        freshness = (
            route.data_freshness
            or "unavailable"
        ).lower()

        if freshness == "fresh":
            return 0

        if freshness == "stale":
            return 1

        if freshness == "historical":
            return 2

        return 3

    # --------------------------------------------------------------
    # Choose recommended route.
    # --------------------------------------------------------------

    recommended = min(
        valid_routes,
        key=lambda route: (
            # 1. Prefer routes that meet user tolerance.
            0 if route.qualifies_preference else 1,

            # 2. Prefer calmer routes.
            route.sensory_score,

            # 3. Prefer fresher pedestrian data.
            freshness_rank(route),

            # 4. Prefer higher sensor coverage.
            -(route.sensor_coverage_ratio or 0),

            # 5. Prefer shorter travel time.
            route.estimated_travel_minutes,

            # 6. Original OSRM order.
            route_order[id(route)],
        ),
    )

    # --------------------------------------------------------------
    # Check whether all usable routes are High.
    # --------------------------------------------------------------

    all_routes_high = all(
        route.sensory_indicator == "High"
        for route in valid_routes
    )

    fastest_minutes = min(
        route.estimated_travel_minutes
        for route in valid_routes
    )

    # --------------------------------------------------------------
    # Build explanation for each route.
    # --------------------------------------------------------------

    for route in routes:
        route.is_recommended = (
            route.route_identifier
            == recommended.route_identifier
        )

        coverage = round(
            (route.sensor_coverage_ratio or 0)
            * 100
        )

        freshness = (
            route.data_freshness
            or "unavailable"
        )

        time_difference = (
            route.estimated_travel_minutes
            - fastest_minutes
        )

        # No reliable sensory score.
        if route.sensory_score is None:
            route.recommendation_explanation = (
                "Pedestrian data is insufficient to assess "
                "this route reliably."
            )
            continue

        # ----------------------------------------------------------
        # Recommended route explanation.
        # ----------------------------------------------------------

        if route.is_recommended:
            if route.qualifies_preference:
                preference_text = (
                    f"Meets crowd preference level "
                    f"{crowd_threshold}."
                )
            else:
                preference_text = (
                    f"Does not fully meet crowd preference "
                    f"level {crowd_threshold}, but it has "
                    f"the strongest available supporting data."
                )

            crowd_level = (
                route.sensory_indicator
                or "Unavailable"
            )

            route.recommendation_explanation = (
                f"Crowd level: {crowd_level}. "
                f"{preference_text} "
                f"Crowd-data coverage is {coverage}% "
                f"with {freshness} pedestrian data."
            )

            if time_difference > 0:
                route.recommendation_explanation += (
                    f" Travel time is {time_difference} minutes "
                    f"longer than the fastest scored route."
                )

        # ----------------------------------------------------------
        # Other route that meets preference.
        # ----------------------------------------------------------

        elif route.qualifies_preference:
            route.recommendation_explanation = (
                f"Meets crowd preference level "
                f"{crowd_threshold}. "
                f"Crowd-data coverage is {coverage}% "
                f"with {freshness} pedestrian data."
            )

        # ----------------------------------------------------------
        # Route exceeds user preference.
        # ----------------------------------------------------------

        else:
            route.recommendation_explanation = (
                f"Exceeds crowd preference level "
                f"{crowd_threshold}. "
                f"Crowd-data coverage is {coverage}% "
                f"with {freshness} pedestrian data."
            )

    # --------------------------------------------------------------
    # Overall recommendation message.
    # --------------------------------------------------------------

    if recommended.qualifies_preference:
        message = (
            "The recommended route meets your crowd preference "
            "and has the strongest available pedestrian-data support."
        )
    else:
        message = (
            "No well-supported route fully meets your crowd preference. "
            "The best supported lower-impact route is recommended."
        )

    if all_routes_high:
        message = (
            "All sufficiently supported routes are classified as "
            "High crowd level. The lowest-impact route with the "
            "strongest available pedestrian data is recommended."
        )

    return {
        "message": message,
        "all_routes_high": all_routes_high,
        "personalised": True,
    }


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------

def persist_route_plan(
    db: Session | None,
    request: RoutePlanningRequest,
    route_build_results: list[RouteBuildResult],
) -> None:
    """
    Saves the journey, routes, nearby transport stops,
    route segments and sensor scores when database
    access is available.

    A database failure does not stop route planning.
    """

    if db is None:
        return

    try:
        # --------------------------------------------------------------
        # 1. Store journey request.
        # --------------------------------------------------------------

        journey_request = JourneyRequest(
            origin_latitude=request.origin_latitude,
            origin_longitude=request.origin_longitude,

            destination_latitude=(
                request.destination_latitude
            ),

            destination_longitude=(
                request.destination_longitude
            ),

            travel_mode=request.travel_mode,

            preferred_crowd_threshold=(
                request.crowd_threshold
            ),

            requested_at=datetime.now(
                timezone.utc
            ),
        )

        db.add(journey_request)
        db.flush()

        # --------------------------------------------------------------
        # 2. Store each route.
        # --------------------------------------------------------------

        for result in route_build_results:
            route = result.response

            route_option = RouteOption(
                journey_request_id=(
                    journey_request.journey_request_id
                ),

                # TODO:
                # Rename google_route_id later.
                google_route_id=route.route_identifier,

                encoded_polyline=route.encoded_polyline,

                estimated_travel_minutes=(
                    route.estimated_travel_minutes
                ),

                sensory_indicator=(
                    route.sensory_indicator
                ),

                total_sensory_score=(
                    Decimal(
                        str(route.sensory_score)
                    )
                    if route.sensory_score is not None
                    else None
                ),

                data_availability_status=(
                    route.pedestrian_data_availability
                ),

                is_recommended=route.is_recommended,

                created_at=datetime.now(
                    timezone.utc
                ),
            )

            db.add(route_option)
            db.flush()

            # Give the frontend response the database route ID.
            route.route_id = route_option.route_id

            # ----------------------------------------------------------
            # 3. Find and store nearby public transport access points.
            # ----------------------------------------------------------
            nearby_transport_stops = (
                find_transport_stops_near_route(
                    db=db,
                    route=result.candidate,
                )
            )

            print(
                "TRANSPORT DEBUG:",
                route.route_identifier,
                "found",
                len(nearby_transport_stops),
                "stops",
            )

            route.transport_stops = [
                TransportStopResponse(
                    stop_id=(
                        transport_stop.stop_id
                    ),

                    stop_name=(
                        transport_stop.stop_name
                    ),

                    mode=(
                        transport_stop.mode
                    ),

                    latitude=float(
                        transport_stop.latitude
                    ),

                    longitude=float(
                        transport_stop.longitude
                    ),

                    distance_m=(
                        distance_m
                    ),

                    stop_sequence=(
                        stop_sequence
                    ),

                    stop_role="near_route",
                )
                for stop_sequence, (
                    transport_stop,
                    distance_m,
                ) in enumerate(
                    nearby_transport_stops,
                    start=1,
                )
            ]


            print(
                "TRANSPORT RESPONSE DEBUG:",
                len(route.transport_stops),
            )


            # ----------------------------------------------------------
            # Save transport stops to database.
            # ----------------------------------------------------------

            for stop_sequence, (
                transport_stop,
                distance_m,
            ) in enumerate(
                nearby_transport_stops,
                start=1,
            ):
                db.add(
                    RouteTransportStop(
                        route_id=(
                            route_option.route_id
                        ),

                        stop_id=(
                            transport_stop.stop_id
                        ),

                        stop_sequence=(
                            stop_sequence
                        ),

                        stop_role=(
                            "near_route"
                        ),

                        distance_m=(
                            distance_m
                        ),
                    )
                )

            # ----------------------------------------------------------
            # 4. Store route segments.
            # ----------------------------------------------------------

            persisted_segments: dict[
                int,
                RouteSegment,
            ] = {}

            for segment in route.route_segments:
                route_segment = RouteSegment(
                    route_id=(
                        route_option.route_id
                    ),

                    segment_sequence=(
                        segment.segment_sequence
                    ),

                    encoded_polyline=(
                        segment.encoded_polyline
                    ),

                    distance_m=(
                        segment.distance_m
                    ),

                    duration_seconds=(
                        segment.duration_seconds
                    ),

                    congestion_level=(
                        segment.congestion_level
                    ),

                    sensory_score=(
                        Decimal(
                            str(
                                segment.sensory_score
                            )
                        )
                        if segment.sensory_score
                        is not None
                        else None
                    ),

                    data_availability_status=(
                        segment.data_availability
                    ),
                )

                db.add(route_segment)
                db.flush()

                # Give the response segment
                # its database ID.
                segment.route_segment_id = (
                    route_segment.route_segment_id
                )

                persisted_segments[
                    segment.segment_sequence
                ] = route_segment

            # ----------------------------------------------------------
            # 5. Store sensor scoring information.
            # ----------------------------------------------------------

            for sensor_score in result.sensor_scores:
                route_segment = (
                    persisted_segments.get(
                        sensor_score.segment_sequence
                    )
                )

                if route_segment is None:
                    continue

                db.add(
                    RouteSensorScore(
                        route_segment_id=(
                            route_segment.route_segment_id
                        ),

                        sensor_id=(
                            sensor_score.sensor_id
                        ),

                        count_source=(
                            sensor_score.count_source
                        ),

                        observed_at=(
                            sensor_score.observed_at
                        ),

                        count_used=(
                            sensor_score.count_used
                        ),

                        score_contribution=(
                            Decimal(
                                str(
                                    sensor_score
                                    .score_contribution
                                )
                            )
                        ),
                    )
                )

        # --------------------------------------------------------------
        # 6. Save everything.
        # --------------------------------------------------------------

        db.commit()

    except Exception as exc:
        # Route generation should still succeed
        # even if persistence fails.
        db.rollback()

        for result in route_build_results:
            result.response.route_id = None

            for segment in (
                result.response.route_segments
            ):
                segment.route_segment_id = None

        logger.warning(
            "Route plan persistence skipped "
            "after database error: %s",
            exc.__class__.__name__,
        )