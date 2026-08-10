from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.sensory_scoring_service import SensoryScoringService


def make_segment(
    sensor_id: int = 1,
    distance_m: float = 100.0,
):
    """
    Creates a fake route segment with one matched pedestrian sensor.
    """

    sensor = SimpleNamespace(
        sensor_id=sensor_id
    )

    matched_sensor = SimpleNamespace(
        sensor=sensor
    )

    return SimpleNamespace(
        segment_sequence=1,
        distance_m=distance_m,
        matched_sensors=[
            matched_sensor
        ],
    )


def make_count(
    count: int,
    sensor_id: int = 1,
):
    """
    Creates a fake pedestrian count.
    """

    return SimpleNamespace(
        sensor_id=sensor_id,
        total_count=count,
        source="realtime",
        observed_at=datetime.now(
            timezone.utc
        ),
    )


@pytest.mark.parametrize(
    "current_count, expected_score, expected_level",
    [
        (50, 0.50, "Low"),
        (100, 1.00, "Moderate"),
        (150, 1.50, "High"),
    ],
)
def test_environmental_crowd_levels(
    current_count,
    expected_score,
    expected_level,
):
    """
    Historical baseline = 100.

    50 / 100  = 0.50 -> Low
    100 / 100 = 1.00 -> Moderate
    150 / 100 = 1.50 -> High
    """

    service = SensoryScoringService()

    segment = make_segment()

    counts = {
        1: make_count(
            current_count
        )
    }

    baselines = {
        1: 100.0
    }

    result = service.score_route(
        segment_matches=[
            segment
        ],
        counts_by_sensor=counts,

        # Level 5 so preference does not interfere
        # with environmental classification.
        crowd_threshold=5,

        historical_baselines=baselines,
    )

    assert result.sensory_score == expected_score
    assert result.sensory_indicator == expected_level


@pytest.mark.parametrize(
    "user_level, expected_qualifies",
    [
        (1, False),
        (2, False),
        (3, True),
        (4, True),
        (5, True),
    ],
)
def test_user_preference_is_separate(
    user_level,
    expected_qualifies,
):
    """
    Keep the environment exactly the same:

        current = 100
        baseline = 100
        score = 1.00
        environmental level = Moderate

    Only change the user's tolerance.
    """

    service = SensoryScoringService()

    segment = make_segment()

    counts = {
        1: make_count(
            100
        )
    }

    baselines = {
        1: 100.0
    }

    result = service.score_route(
        segment_matches=[
            segment
        ],
        counts_by_sensor=counts,
        crowd_threshold=user_level,
        historical_baselines=baselines,
    )

    # IMPORTANT:
    # The physical environment should remain Moderate
    # regardless of the user's preference.
    assert result.sensory_score == 1.00
    assert result.sensory_indicator == "Moderate"

    # Only Meets / Exceeds should change.
    assert (
        result.qualifies_preference
        == expected_qualifies
    )


def test_level_1_exceeds_moderate_route():
    """
    Score = 1.00
    Level 1 limit = 0.55
    1.00 > 0.55
    therefore it exceeds preference.
    """

    service = SensoryScoringService()

    result = service.score_route(
        segment_matches=[
            make_segment()
        ],
        counts_by_sensor={
            1: make_count(100)
        },
        crowd_threshold=1,
        historical_baselines={
            1: 100.0
        },
    )

    assert result.sensory_indicator == "Moderate"

    assert result.qualifies_preference is False

    assert result.threshold_exceeded is True


def test_level_4_accepts_moderate_route():
    """
    Score = 1.00
    Level 4 limit = 1.25
    1.00 <= 1.25
    therefore it meets preference.
    """

    service = SensoryScoringService()

    result = service.score_route(
        segment_matches=[
            make_segment()
        ],
        counts_by_sensor={
            1: make_count(100)
        },
        crowd_threshold=4,
        historical_baselines={
            1: 100.0
        },
    )

    assert result.sensory_indicator == "Moderate"

    assert result.qualifies_preference is True

    assert result.threshold_exceeded is False