from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.pedestrian_repository import PedestrianCountRecord
from app.services.data_freshness_service import (
    DataFreshnessService,
    FreshnessStatus,
    ensure_aware,
    least_fresh,
)
from app.services.sensor_matching_service import SegmentSensorMatch


# ---------------------------------------------------------------------------
# Scoring configuration
# ---------------------------------------------------------------------------

# Used only when a historical baseline is unavailable
# for a pedestrian sensor.
DEFAULT_HISTORICAL_BASELINE_COUNT = 300.0

# Environmental crowd classification.
#
# score = current pedestrian count / historical baseline
#
# < 0.80       -> Low
# 0.80 - 1.24  -> Moderate
# >= 1.25      -> High
MODERATE_SENSORY_SCORE_THRESHOLD = 0.80
HIGH_SENSORY_SCORE_THRESHOLD = 1.25

# Minimum percentage of route segments that must
# have pedestrian data before we trust the route score.
MINIMUM_SENSOR_COVERAGE_RATIO = 0.5


# ---------------------------------------------------------------------------
# User crowd tolerance
# ---------------------------------------------------------------------------

# User-selected crowd tolerance.
#
# This is separate from Low / Moderate / High.
#
# 1 = very low tolerance
# 5 = high tolerance
PREFERENCE_SCORE_LIMITS = {
    1: 0.55,
    2: 0.80,
    3: 1.00,
    4: 1.25,
    5: 1.50,
}


def acceptable_congestion_score(
    preference_level: int,
) -> float:
    """
    Convert the user's crowd tolerance level
    into the maximum acceptable congestion score.

    This does NOT decide whether the route itself
    is Low, Moderate or High.

    It only determines whether the route meets
    the individual user's preference.
    """

    if preference_level not in PREFERENCE_SCORE_LIMITS:
        raise ValueError(
            "Crowd threshold must be between 1 and 5."
        )

    return PREFERENCE_SCORE_LIMITS[
        preference_level
    ]


# ---------------------------------------------------------------------------
# Scoring models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sensory scoring service
# ---------------------------------------------------------------------------

class SensoryScoringService:
    """
    Scores pedestrian exposure for a route.

    There are two separate concepts:

    1. Environmental crowd condition

       Current pedestrian count
       divided by historical baseline.

       Example:

           current = 120
           baseline = 100

           score = 1.20

           -> Moderate crowd

    2. User crowd preference

       The environmental score is compared
       against the user's selected tolerance.

       Example:

           score = 1.20
           user level 2 limit = 0.80

           -> Exceeds preference

       Another user:

           score = 1.20
           user level 4 limit = 1.25

           -> Meets preference

    The actual Low / Moderate / High crowd
    condition therefore stays independent
    from the individual user's preference.
    """

    def __init__(
        self,
        freshness_service: DataFreshnessService | None = None,
    ) -> None:
        self.freshness_service = (
            freshness_service
            or DataFreshnessService()
        )

    def score_route(
        self,
        segment_matches: list[SegmentSensorMatch],
        counts_by_sensor: dict[
            int,
            PedestrianCountRecord,
        ],
        crowd_threshold: int,
        historical_baselines: dict[
            int,
            float,
        ]
        | None = None,
        now: datetime | None = None,
    ) -> RouteScore:

        current_time = (
            ensure_aware(
                now
                or datetime.now(
                    timezone.utc
                )
            )
            or datetime.now(
                timezone.utc
            )
        )

        baselines = (
            historical_baselines
            or {}
        )

        # --------------------------------------------------------------
        # Convert user preference to acceptable score.
        # --------------------------------------------------------------

        preference_limit = (
            acceptable_congestion_score(
                crowd_threshold
            )
        )

        segment_scores: list[
            SegmentScore
        ] = []

        weighted_scores: list[
            tuple[float, float]
        ] = []

        matched_sensor_ids: set[
            int
        ] = set()

        total_segments = len(
            segment_matches
        )

        # --------------------------------------------------------------
        # Score each route segment.
        # --------------------------------------------------------------

        for segment_match in segment_matches:

            matched_sensor_ids.update(
                match.sensor.sensor_id
                for match
                in segment_match.matched_sensors
            )

            segment_weight = float(
                segment_match.distance_m
                or 1
            )

            records = [
                counts_by_sensor[
                    match.sensor.sensor_id
                ]
                for match
                in segment_match.matched_sensors
                if match.sensor.sensor_id
                in counts_by_sensor
            ]

            # ----------------------------------------------------------
            # No pedestrian data for this segment.
            # ----------------------------------------------------------

            if not records:
                segment_scores.append(
                    SegmentScore(
                        segment_sequence=(
                            segment_match.segment_sequence
                        ),
                        matched_sensor_count=len(
                            segment_match.matched_sensors
                        ),
                        score=None,
                        congestion_level=None,
                        data_availability=(
                            "unavailable"
                        ),
                        weight=segment_weight,
                        pedestrian_count=None,
                        threshold_exceeded=None,
                        data_source=(
                            "unavailable"
                        ),
                        observed_at=None,
                        freshness_status=(
                            "unavailable"
                        ),
                    )
                )

                continue

            # ----------------------------------------------------------
            # Calculate environmental congestion score.
            #
            # score =
            # current pedestrian count
            # ------------------------
            # historical baseline
            # ----------------------------------------------------------

            normalised_values = []

            for record in records:

                baseline = (
                    baselines.get(
                        record.sensor_id
                    )
                    or DEFAULT_HISTORICAL_BASELINE_COUNT
                )

                congestion_ratio = (
                    record.total_count
                    / max(
                        1.0,
                        float(baseline),
                    )
                )

                normalised_values.append(
                    congestion_ratio
                )

            # ----------------------------------------------------------
            # Average congestion score for this segment.
            # ----------------------------------------------------------

            segment_score = round(
                sum(
                    normalised_values
                )
                / len(
                    normalised_values
                ),
                2,
            )

            average_count = round(
                sum(
                    record.total_count
                    for record
                    in records
                )
                / len(records)
            )

            # ----------------------------------------------------------
            # Data freshness.
            # ----------------------------------------------------------

            freshnesses = [
                self.freshness_service.classify(
                    record.observed_at,
                    record.source,
                    current_time,
                )
                for record
                in records
            ]

            observed_values = [
                ensure_aware(
                    record.observed_at
                )
                for record
                in records
            ]

            valid_observed_values = [
                value
                for value
                in observed_values
                if value is not None
            ]

            observed_at = (
                max(
                    valid_observed_values
                )
                if valid_observed_values
                else None
            )

            source = (
                "realtime"
                if any(
                    record.source
                    == "realtime"
                    for record
                    in records
                )
                else "historical"
            )

            # ----------------------------------------------------------
            # User preference comparison.
            #
            # This is separate from Low / Moderate / High.
            # ----------------------------------------------------------

            segment_threshold_exceeded = (
                segment_score
                > preference_limit
            )

            # ----------------------------------------------------------
            # Add segment to route weighted score.
            # ----------------------------------------------------------

            weighted_scores.append(
                (
                    segment_score,
                    segment_weight,
                )
            )

            segment_scores.append(
                SegmentScore(
                    segment_sequence=(
                        segment_match.segment_sequence
                    ),
                    matched_sensor_count=len(
                        segment_match.matched_sensors
                    ),
                    score=segment_score,

                    # Environmental condition.
                    congestion_level=(
                        self._congestion_level(
                            segment_score
                        )
                    ),

                    data_availability=(
                        "available"
                    ),

                    weight=segment_weight,

                    pedestrian_count=(
                        average_count
                    ),

                    # Personal preference.
                    threshold_exceeded=(
                        segment_threshold_exceeded
                    ),

                    data_source=source,

                    observed_at=(
                        observed_at
                    ),

                    freshness_status=(
                        least_fresh(
                            freshnesses
                        )
                    ),
                )
            )

        # --------------------------------------------------------------
        # Determine data coverage.
        # --------------------------------------------------------------

        scored_segments = [
            segment
            for segment
            in segment_scores
            if segment.score
            is not None
        ]

        coverage_ratio = (
            round(
                len(
                    scored_segments
                )
                / total_segments,
                2,
            )
            if total_segments
            else 0.0
        )

        # --------------------------------------------------------------
        # No pedestrian data at all.
        # --------------------------------------------------------------

        if not weighted_scores:
            return RouteScore(
                sensory_score=None,
                sensory_indicator=(
                    "Unavailable"
                ),
                data_availability=(
                    "unavailable"
                ),
                matched_sensor_count=len(
                    matched_sensor_ids
                ),
                sensor_coverage_ratio=(
                    coverage_ratio
                ),
                warning_message=(
                    "Pedestrian sensor data is unavailable "
                    "for this route, so congestion information "
                    "cannot be fully confirmed and personalised "
                    "recommendations cannot be generated."
                ),
                segment_scores=(
                    segment_scores
                ),
                threshold_exceeded=None,
                qualifies_preference=False,
                data_freshness=(
                    "unavailable"
                ),
                observed_at=None,
                updated_at=(
                    current_time
                ),
            )

        # --------------------------------------------------------------
        # Overall route data freshness.
        # --------------------------------------------------------------

        route_freshness = (
            least_fresh(
                [
                    segment.freshness_status
                    for segment
                    in scored_segments
                ]
            )
        )

        route_observed_values = [
            segment.observed_at
            for segment
            in scored_segments
            if segment.observed_at
            is not None
        ]

        observed_at = (
            max(
                route_observed_values
            )
            if route_observed_values
            else None
        )

        # --------------------------------------------------------------
        # Distance-weighted overall route score.
        # --------------------------------------------------------------

        total_weight = sum(
            weight
            for _,
            weight
            in weighted_scores
        )

        route_score = round(
            sum(
                score * weight
                for score,
                weight
                in weighted_scores
            )
            / total_weight,
            2,
        )

        warning_message = None

        availability = (
            "available"
            if len(
                scored_segments
            )
            == total_segments
            else "partial"
        )

        # --------------------------------------------------------------
        # Not enough sensor coverage.
        # --------------------------------------------------------------

        if (
            coverage_ratio
            < MINIMUM_SENSOR_COVERAGE_RATIO
        ):
            route_score = None

            availability = (
                "partial"
            )

            warning_message = (
                "Pedestrian data coverage is too limited "
                "for personalised route recommendations."
            )

        elif (
            len(
                scored_segments
            )
            != total_segments
        ):
            warning_message = (
                "Pedestrian data is partial for this route, "
                "so congestion information cannot be fully confirmed."
            )

        elif (
            route_freshness
            == "stale"
        ):
            warning_message = (
                "The latest pedestrian readings are stale; "
                "current congestion cannot be fully confirmed."
            )

        elif (
            route_freshness
            == "historical"
        ):
            warning_message = (
                "This route uses historical pedestrian data "
                "rather than live conditions."
            )

        # --------------------------------------------------------------
        # Final environmental + personal result.
        # --------------------------------------------------------------

        if route_score is None:

            indicator = (
                "Unavailable"
            )

            threshold_value: (
                bool | None
            ) = None

            qualifies = False

        else:

            # ----------------------------------------------------------
            # Environmental classification.
            #
            # Same route condition for every user.
            # ----------------------------------------------------------

            indicator = (
                self._congestion_level(
                    route_score
                ).capitalize()
            )

            # ----------------------------------------------------------
            # User preference comparison.
            #
            # Changes depending on selected tolerance.
            # ----------------------------------------------------------

            threshold_value = (
                route_score
                > preference_limit
            )

            qualifies = (
                not threshold_value
            )

        return RouteScore(
            sensory_score=(
                route_score
            ),

            sensory_indicator=(
                indicator
            ),

            data_availability=(
                availability
            ),

            matched_sensor_count=len(
                matched_sensor_ids
            ),

            sensor_coverage_ratio=(
                coverage_ratio
            ),

            warning_message=(
                warning_message
            ),

            segment_scores=(
                segment_scores
            ),

            threshold_exceeded=(
                threshold_value
            ),

            qualifies_preference=(
                qualifies
            ),

            data_freshness=(
                route_freshness
            ),

            observed_at=(
                observed_at
            ),

            updated_at=(
                current_time
            ),
        )

    # -----------------------------------------------------------------------
    # Environmental crowd classification.
    # -----------------------------------------------------------------------

    @staticmethod
    def _congestion_level(
        score: float,
    ) -> str:
        """
        Convert an environmental congestion score
        into Low / Moderate / High.

        This classification is independent
        of the user's crowd preference.
        """

        if (
            score
            >= HIGH_SENSORY_SCORE_THRESHOLD
        ):
            return "high"

        if (
            score
            >= MODERATE_SENSORY_SCORE_THRESHOLD
        ):
            return "moderate"

        return "low"