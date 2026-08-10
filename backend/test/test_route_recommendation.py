from app.api.routes import mark_recommended_route
from app.schemas.route_planning import RouteOptionResponse


def make_route(
    identifier: str,
    score: float | None,
    indicator: str,
    qualifies: bool,
    coverage: float,
    freshness: str,
    availability: str = "available",
    minutes: int = 10,
):
    """
    Create a fake route for testing recommendation logic.
    """

    return RouteOptionResponse(
        route_identifier=identifier,
        points=[],
        encoded_polyline="",
        estimated_travel_minutes=minutes,
        travel_mode="walking",

        sensory_score=score,
        sensory_indicator=indicator,

        is_recommended=False,

        pedestrian_data_availability=availability,
        data_availability_status=availability,

        matched_sensor_count=1,
        sensor_coverage_ratio=coverage,

        route_segments=[],

        warning_message=None,

        threshold_exceeded=not qualifies,
        qualifies_preference=qualifies,

        data_freshness=freshness,

        observed_at=None,
        updated_at=None,
    )


def get_recommended(routes):
    return next(
        route
        for route in routes
        if route.is_recommended
    )


def test_lower_score_can_beat_full_coverage_when_data_is_sufficient():
    """
    Route A:
        Moderate
        score 1.00
        100% coverage
        fresh

    Route B:
        Low
        score 0.50
        70% coverage
        fresh

    Both routes have enough usable data.

    Because both meet the user's preference,
    the calmer route should be recommended
    even though its coverage is lower.
    """

    route_a = make_route(
        identifier="route_a",
        score=1.00,
        indicator="Moderate",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
        availability="available",
    )

    route_b = make_route(
        identifier="route_b",
        score=0.50,
        indicator="Low",
        qualifies=True,
        coverage=0.70,
        freshness="fresh",
        availability="partial",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_b"
    )


def test_meeting_preference_beats_lower_score_when_data_quality_same():
    """
    Same data reliability.

    Route A:
        score = 0.90
        meets preference

    Route B:
        score = 0.60
        exceeds preference

    Route A should win because personal
    preference is checked before score.
    """

    route_a = make_route(
        identifier="route_a",
        score=0.90,
        indicator="Moderate",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
    )

    route_b = make_route(
        identifier="route_b",
        score=0.60,
        indicator="Low",
        qualifies=False,
        coverage=1.0,
        freshness="fresh",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=2,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_a"
    )


def test_lower_sensory_score_wins_when_other_factors_same():
    """
    Same reliability.
    Both meet preference.

    Lower crowd score should win.
    """

    route_a = make_route(
        identifier="route_a",
        score=1.00,
        indicator="Moderate",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
    )

    route_b = make_route(
        identifier="route_b",
        score=0.60,
        indicator="Low",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_b"
    )


def test_fresher_data_wins_when_preference_and_score_are_equal():
    """
    Same preference result.
    Same sensory score.

    Fresher pedestrian data should win.
    """

    route_a = make_route(
        identifier="route_a",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=1.0,
        freshness="stale",
    )

    route_b = make_route(
        identifier="route_b",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=0.80,
        freshness="fresh",
        availability="partial",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_b"
    )


def test_higher_coverage_wins_when_scores_and_freshness_are_equal():
    """
    If preference, score and freshness
    are the same, higher coverage wins.
    """

    route_a = make_route(
        identifier="route_a",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=0.90,
        freshness="fresh",
        availability="partial",
    )

    route_b = make_route(
        identifier="route_b",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=0.60,
        freshness="fresh",
        availability="partial",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_a"
    )


def test_shorter_route_wins_when_everything_else_is_equal():
    """
    Travel time is a late tie-breaker.
    """

    route_a = make_route(
        identifier="route_a",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
        minutes=15,
    )

    route_b = make_route(
        identifier="route_b",
        score=0.70,
        indicator="Low",
        qualifies=True,
        coverage=1.0,
        freshness="fresh",
        minutes=10,
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "route_b"
    )


def test_route_without_score_is_not_recommended():
    """
    A route with unavailable sensory data
    should not beat a usable route.
    """

    route_a = make_route(
        identifier="unknown_route",
        score=None,
        indicator="Unavailable",
        qualifies=False,
        coverage=0.20,
        freshness="unavailable",
        availability="partial",
    )

    route_b = make_route(
        identifier="usable_route",
        score=0.80,
        indicator="Moderate",
        qualifies=True,
        coverage=0.80,
        freshness="fresh",
        availability="partial",
    )

    routes = [
        route_a,
        route_b,
    ]

    mark_recommended_route(
        routes,
        crowd_threshold=3,
    )

    recommended = get_recommended(
        routes
    )

    assert (
        recommended.route_identifier
        == "usable_route"
    )