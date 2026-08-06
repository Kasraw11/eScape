from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_route_congestion_service, mark_recommended_route
from app.main import app
from app.models.pedestrian_count import RealtimePedestrianCount
from app.models.sensor_location import SensorLocation
from app.repositories.pedestrian_repository import PedestrianCountRecord, SensorRecord
from app.schemas.route_planning import RouteCongestionResponse, RouteOptionResponse, RoutePlanningRequest, RouteSegmentResponse
from app.services.data_freshness_service import DataFreshnessService
from app.services.pedestrian_ingestion_service import (
    MelbournePedestrianClient,
    MelbournePedestrianDataError,
    PedestrianIngestionService,
    validate_reading,
)
from app.services.route_congestion_service import RouteCongestionService, is_meaningful_change
from app.services.sensor_matching_service import MatchedSensor, SegmentSensorMatch
from app.services.sensory_scoring_service import SensoryScoringService, acceptable_congestion_score


VALID_REQUEST = {
    "origin_latitude": -37.8136,
    "origin_longitude": 144.9631,
    "destination_latitude": -37.8183,
    "destination_longitude": 144.9671,
    "travel_mode": "walking",
}


@pytest.mark.parametrize("threshold", [1, 2, 3, 4, 5])
def test_threshold_accepts_valid_scale(threshold: int) -> None:
    request = RoutePlanningRequest(**VALID_REQUEST, preferred_crowd_threshold=threshold)
    assert request.crowd_threshold == threshold
    assert request.preferred_crowd_threshold == threshold


@pytest.mark.parametrize("threshold", [0, 6, "calm"])
def test_threshold_rejects_invalid_values(threshold) -> None:
    with pytest.raises(ValueError):
        RoutePlanningRequest(**VALID_REQUEST, preferred_crowd_threshold=threshold)


def make_match(sensor_id: int = 1) -> SegmentSensorMatch:
    return SegmentSensorMatch(
        segment_sequence=1,
        distance_m=500,
        matched_sensors=[
            MatchedSensor(
                sensor=SensorRecord(sensor_id, "Test sensor", -37.8136, 144.9631),
                distance_m=1,
                route_point_index=0,
            )
        ],
    )


def test_route_planning_applies_preference_without_changing_measured_score() -> None:
    now = datetime.now(timezone.utc)
    records = {1: PedestrianCountRecord(1, 100, now, "realtime")}
    service = SensoryScoringService()
    strict = service.score_route([make_match()], records, 1, {1: 100}, now)
    tolerant = service.score_route([make_match()], records, 5, {1: 100}, now)

    assert strict.sensory_score == tolerant.sensory_score == 1
    assert strict.threshold_exceeded is True
    assert strict.qualifies_preference is False
    assert tolerant.threshold_exceeded is False
    assert tolerant.qualifies_preference is True


@pytest.mark.parametrize(
    ("count", "expected_level"),
    [(50, "low"), (150, "high")],
)
def test_segment_congestion_classification(count: int, expected_level: str) -> None:
    now = datetime.now(timezone.utc)
    result = SensoryScoringService().score_route(
        [make_match()],
        {1: PedestrianCountRecord(1, count, now, "realtime")},
        3,
        {1: 100},
        now,
    )
    assert result.segment_scores[0].congestion_level == expected_level


def test_unavailable_segment_is_not_fabricated_as_low() -> None:
    result = SensoryScoringService().score_route([make_match()], {}, 3)
    assert result.segment_scores[0].congestion_level is None
    assert result.segment_scores[0].freshness_status == "unavailable"
    assert result.sensory_indicator == "Unavailable"


@pytest.mark.parametrize(
    ("source", "age", "expected"),
    [
        ("realtime", timedelta(seconds=60), "live"),
        ("realtime", timedelta(minutes=5), "recent"),
        ("realtime", timedelta(minutes=11), "stale"),
        ("historical", timedelta(days=30), "historical"),
        (None, None, "unavailable"),
    ],
)
def test_data_freshness_policy(source, age, expected: str) -> None:
    now = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    observed_at = now - age if age is not None else None
    assert DataFreshnessService(120, 600).classify(observed_at, source, now) == expected


def route_response(identifier: str, score: float | None, level: str, exceeded: bool | None) -> RouteOptionResponse:
    return RouteOptionResponse(
        route_identifier=identifier,
        estimated_travel_minutes=12,
        travel_mode="walking",
        sensory_score=score,
        sensory_indicator=level,
        is_recommended=False,
        pedestrian_data_availability="unavailable" if score is None else "available",
        data_availability_status="unavailable" if score is None else "available",
        matched_sensor_count=0 if score is None else 1,
        sensor_coverage_ratio=0 if score is None else 1,
        threshold_exceeded=exceeded,
        qualifies_preference=exceeded is False,
        route_segments=[
            RouteSegmentResponse(
                segment_sequence=1,
                matched_sensor_count=0 if score is None else 1,
                congestion_level=None if score is None else "high",
                sensory_score=score,
                data_availability="unavailable" if score is None else "available",
            )
        ],
    )


def test_all_routes_high_uses_lowest_impact_fallback() -> None:
    routes = [route_response("higher", 2.0, "High", True), route_response("lower", 1.5, "High", True)]
    result = mark_recommended_route(routes, 2)
    assert result["all_routes_high"] is True
    assert next(route for route in routes if route.is_recommended).route_identifier == "lower"
    assert "still exceeds" in routes[1].recommendation_explanation


def test_all_routes_unavailable_disables_personalised_recommendation() -> None:
    routes = [route_response("missing-a", None, "Unavailable", None), route_response("missing-b", None, "Unavailable", None)]
    result = mark_recommended_route(routes, 3)
    assert result["personalised"] is False
    assert not any(route.is_recommended for route in routes)


def test_multiple_qualifying_alternatives_are_ranked_by_score_time_and_order() -> None:
    selected = SimpleNamespace(route_id=1)
    scored_routes = [
        (selected, SimpleNamespace(threshold_exceeded=True, sensory_score=2.0, qualifies_preference=False, sensory_indicator="High")),
        (SimpleNamespace(route_id=2, google_route_id="calm-slower", estimated_travel_minutes=15), SimpleNamespace(sensory_score=0.7, qualifies_preference=True, sensory_indicator="Low", threshold_exceeded=False)),
        (SimpleNamespace(route_id=3, google_route_id="calm-faster", estimated_travel_minutes=10), SimpleNamespace(sensory_score=0.7, qualifies_preference=True, sensory_indicator="Low", threshold_exceeded=False)),
    ]
    alternatives = RouteCongestionService._rank_alternatives(selected, scored_routes, 3)
    assert [alternative.route_id for alternative in alternatives] == [3, 2]
    assert all("Meets crowd preference" in alternative.recommendation_explanation for alternative in alternatives)


def test_no_qualifying_alternative_returns_lowest_impact_honest_fallback() -> None:
    selected = SimpleNamespace(route_id=1)
    scored_routes = [
        (selected, SimpleNamespace(threshold_exceeded=True, sensory_score=2.0, qualifies_preference=False, sensory_indicator="High")),
        (SimpleNamespace(route_id=2, google_route_id="fallback", estimated_travel_minutes=12), SimpleNamespace(sensory_score=1.4, qualifies_preference=False, sensory_indicator="High", threshold_exceeded=True)),
    ]
    alternatives = RouteCongestionService._rank_alternatives(selected, scored_routes, 2)
    assert alternatives[0].route_id == 2
    assert alternatives[0].threshold_exceeded is True
    assert "still exceeds" in alternatives[0].recommendation_explanation


@pytest.mark.parametrize(
    "change",
    [
        ("low", "high", False, True, "available", "available", 0.8, 1.4),
        ("low", "low", False, True, "available", "available", 0.8, 1.1),
        ("low", None, False, None, "available", "unavailable", 0.8, None),
        ("low", "low", False, False, "available", "available", 0.8, 1.1),
    ],
)
def test_meaningful_change_detection(change) -> None:
    assert is_meaningful_change(*change) is True


def test_unchanged_or_small_noise_does_not_alert() -> None:
    assert is_meaningful_change("low", "low", False, False, "available", "available", 0.8, 0.9) is False


def test_alert_deduplication_returns_no_repeated_notification() -> None:
    class AlertDb:
        def scalar(self, statement):
            return object()

    service = object.__new__(RouteCongestionService)
    service.db = AlertDb()
    route = SimpleNamespace(route_id=7)
    segment = SimpleNamespace(route_segment_id=9, segment_sequence=2)
    score = SimpleNamespace(congestion_level="high", threshold_exceeded=True)
    route_score = SimpleNamespace(sensory_indicator="High", threshold_exceeded=True)
    assert service._create_notification(route, (segment, score), route_score, datetime.now(timezone.utc)) is None


def congestion_payload() -> RouteCongestionResponse:
    now = datetime.now(timezone.utc)
    return RouteCongestionResponse(
        route_id=1,
        route_identifier="route-one",
        congestion_status="Low",
        sensory_score=0.5,
        sensory_indicator="Low",
        threshold_exceeded=False,
        preferred_crowd_threshold=3,
        updated_at=now,
        data_freshness="live",
        route_segments=[RouteSegmentResponse(segment_sequence=1, matched_sensor_count=1, congestion_level="low", sensory_score=0.5, data_availability="available")],
    )


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_congestion_update_endpoint(client: TestClient) -> None:
    fake = SimpleNamespace(refresh=lambda route_id: congestion_payload(), db=SimpleNamespace(rollback=lambda: None))
    app.dependency_overrides[get_route_congestion_service] = lambda: fake
    response = client.get("/api/routes/1/congestion")
    assert response.status_code == 200
    assert response.json()["data_freshness"] == "live"


def test_congestion_endpoint_unknown_route(client: TestClient) -> None:
    fake = SimpleNamespace(refresh=lambda route_id: None, db=SimpleNamespace(rollback=lambda: None))
    app.dependency_overrides[get_route_congestion_service] = lambda: fake
    assert client.get("/api/routes/999/congestion").status_code == 404


def test_congestion_endpoint_requires_postgresql(client: TestClient) -> None:
    app.dependency_overrides[get_route_congestion_service] = lambda: None
    response = client.get("/api/routes/1/congestion")
    assert response.status_code == 503
    assert response.json()["detail"] == "Congestion refresh requires a configured database"


def test_congestion_endpoint_database_failure_is_safe(client: TestClient) -> None:
    rollback = SimpleNamespace(called=False)
    def mark_rollback():
        rollback.called = True
    def fail(route_id):
        raise RuntimeError("postgres password must remain private")
    fake = SimpleNamespace(refresh=fail, db=SimpleNamespace(rollback=mark_rollback))
    app.dependency_overrides[get_route_congestion_service] = lambda: fake
    response = client.get("/api/routes/1/congestion")
    assert response.status_code == 503
    assert "password" not in response.text
    assert rollback.called is True


def sample_reading(**overrides):
    return {
        "location_id": 3,
        "sensing_datetime": "2026-08-06T01:02:00+00:00",
        "direction_1": 10,
        "direction_2": 12,
        "total_of_directions": 22,
        "id": "reading-3",
        **overrides,
    }


def test_ingestion_validation_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        validate_reading(sample_reading(total_of_directions=-1))


def test_ingestion_inserts_latest_known_sensor_and_skips_duplicates() -> None:
    class FakeDb:
        def __init__(self):
            self.added = []
        def get(self, model, identifier):
            return SimpleNamespace(sensor_id=identifier) if model is SensorLocation else None
        def scalar(self, statement):
            return None
        def add(self, item):
            self.added.append(item)

    db = FakeDb()
    stats = PedestrianIngestionService(db).ingest([sample_reading(), sample_reading()])
    assert stats.inserted == 1
    assert stats.skipped == 1
    assert isinstance(db.added[0], RealtimePedestrianCount)


def test_ingestion_updates_an_existing_reading_without_duplicating_it() -> None:
    existing = SimpleNamespace(
        direction_1_count=1,
        direction_2_count=2,
        total_count=3,
        source_record_id="old-reading",
    )

    class FakeDb:
        def get(self, model, identifier):
            return SimpleNamespace(sensor_id=identifier)
        def scalar(self, statement):
            return existing
        def add(self, item):
            raise AssertionError("An existing reading should be updated, not inserted")

    stats = PedestrianIngestionService(FakeDb()).ingest([sample_reading()])
    assert stats.updated == 1
    assert stats.inserted == 0
    assert existing.total_count == 22


def test_melbourne_data_service_failure_preserves_safe_error() -> None:
    async def run_failure():
        transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "offline"}))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(MelbournePedestrianDataError):
                await MelbournePedestrianClient().fetch_latest(client)
    asyncio.run(run_failure())


def test_preference_mapping_is_central_and_monotonic() -> None:
    values = [acceptable_congestion_score(level) for level in range(1, 6)]
    assert values == sorted(values)
    assert len(set(values)) == 5
