from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.api.routes import (
    RouteBuildResult,
    SegmentSensorScorePersistence,
    get_google_maps_service,
    get_pedestrian_repository,
    persist_route_plan,
)
from app.main import app
from app.repositories.pedestrian_repository import PedestrianCountRecord, SensorRecord
from app.schemas.route_planning import RouteOptionResponse, RoutePlanningRequest, RouteSegmentResponse
from app.services.google_maps_service import GoogleMapsServiceError, RouteCandidate, RouteSegmentCandidate
from app.services.sensor_matching_service import MatchedSensor, SegmentSensorMatch
from app.services.sensory_scoring_service import SensoryScoringService


VALID_REQUEST = {
    "origin_latitude": -37.8136,
    "origin_longitude": 144.9631,
    "destination_latitude": -37.8183,
    "destination_longitude": 144.9671,
    "travel_mode": "walking",
    "crowd_threshold": 3,
}


class FakeGoogleMapsService:
    def __init__(self, routes: list[RouteCandidate] | None = None, should_fail: bool = False) -> None:
        self.routes = routes or []
        self.should_fail = should_fail

    async def get_route_alternatives(self, request: RoutePlanningRequest) -> list[RouteCandidate]:
        if self.should_fail:
            raise GoogleMapsServiceError("fake failure")
        return self.routes


class FakePedestrianRepository:
    def __init__(
        self,
        sensors: list[SensorRecord] | None = None,
        counts: dict[int, PedestrianCountRecord] | None = None,
    ) -> None:
        self.sensors = sensors or []
        self.counts = counts or {}

    def get_sensors_in_bounds(self, min_latitude, max_latitude, min_longitude, max_longitude):
        return [
            sensor
            for sensor in self.sensors
            if min_latitude <= sensor.latitude <= max_latitude
            and min_longitude <= sensor.longitude <= max_longitude
        ]

    def get_latest_counts(self, sensor_ids):
        return {sensor_id: self.counts[sensor_id] for sensor_id in sensor_ids if sensor_id in self.counts}


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def override_services(
    routes: list[RouteCandidate],
    sensors: list[SensorRecord] | None = None,
    counts: dict[int, PedestrianCountRecord] | None = None,
    google_failure: bool = False,
) -> None:
    app.dependency_overrides[get_google_maps_service] = lambda: FakeGoogleMapsService(
        routes=routes,
        should_fail=google_failure,
    )
    app.dependency_overrides[get_pedestrian_repository] = lambda: FakePedestrianRepository(
        sensors=sensors,
        counts=counts,
    )


def make_route(route_identifier: str, point: tuple[float, float], minutes: int = 12) -> RouteCandidate:
    return RouteCandidate(
        route_identifier=route_identifier,
        encoded_polyline=None,
        points=[point],
        estimated_travel_minutes=minutes,
        segments=[
            RouteSegmentCandidate(
                segment_sequence=1,
                encoded_polyline=None,
                points=[point],
                distance_m=500,
                duration_seconds=minutes * 60,
            )
        ],
    )


def make_two_segment_route(route_identifier: str) -> RouteCandidate:
    return RouteCandidate(
        route_identifier=route_identifier,
        encoded_polyline=None,
        points=[(-37.8136, 144.9631), (-37.8183, 144.9671)],
        estimated_travel_minutes=12,
        segments=[
            RouteSegmentCandidate(
                segment_sequence=1,
                encoded_polyline=None,
                points=[(-37.8136, 144.9631)],
                distance_m=600,
                duration_seconds=360,
            ),
            RouteSegmentCandidate(
                segment_sequence=2,
                encoded_polyline=None,
                points=[(-37.8183, 144.9671)],
                distance_m=600,
                duration_seconds=360,
            ),
        ],
    )


def count(sensor_id: int, total_count: int) -> PedestrianCountRecord:
    return PedestrianCountRecord(
        sensor_id=sensor_id,
        total_count=total_count,
        observed_at=datetime.now(timezone.utc),
        source="historical",
    )


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "eScape API is running"}


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_route_planning_cors_preflight_allows_local_frontend(client: TestClient, origin: str) -> None:
    response = client.options(
        "/api/routes/plan",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]


def test_database_health_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "engine", None)
    response = client.get("/health/database")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}


def test_database_health_connection_failure_returns_safe_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class UnavailableEngine:
        def connect(self):
            raise RuntimeError("database password must not appear in the response")

    monkeypatch.setattr(main_module, "engine", UnavailableEngine())
    response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
    assert "password" not in response.text


def test_valid_route_planning_request_returns_contract(client: TestClient) -> None:
    override_services(routes=[make_route("route_a", (-37.8136, 144.9631))])
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["routes"]) == 1
    assert payload["routes"][0]["route_identifier"] == "route_a"
    assert payload["routes"][0]["travel_mode"] == "walking"
    assert "estimated_travel_minutes" in payload["routes"][0]
    assert payload["routes"][0]["sensor_coverage_ratio"] == 0
    assert payload["routes"][0]["data_availability_status"] == payload["routes"][0]["pedestrian_data_availability"]


def test_valid_transit_request(client: TestClient) -> None:
    override_services(routes=[make_route("route_transit", (-37.8136, 144.9631))])
    response = client.post("/api/routes/plan", json=VALID_REQUEST | {"travel_mode": "transit"})
    assert response.status_code == 200
    assert response.json()["routes"][0]["travel_mode"] == "transit"


def test_invalid_latitude_is_rejected(client: TestClient) -> None:
    response = client.post("/api/routes/plan", json=VALID_REQUEST | {"origin_latitude": 95})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_invalid_longitude_is_rejected(client: TestClient) -> None:
    response = client.post("/api/routes/plan", json=VALID_REQUEST | {"origin_longitude": 181})
    assert response.status_code == 422


def test_unsupported_travel_mode_is_rejected(client: TestClient) -> None:
    response = client.post("/api/routes/plan", json=VALID_REQUEST | {"travel_mode": "driving"})
    assert response.status_code == 422


def test_identical_origin_and_destination_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/routes/plan",
        json=VALID_REQUEST
        | {
            "destination_latitude": VALID_REQUEST["origin_latitude"],
            "destination_longitude": VALID_REQUEST["origin_longitude"],
        },
    )
    assert response.status_code == 422
    assert "Origin and destination must be different" in response.text


def test_location_outside_melbourne_cbd_is_rejected(client: TestClient) -> None:
    response = client.post("/api/routes/plan", json=VALID_REQUEST | {"destination_latitude": -37.9})
    assert response.status_code == 422
    assert "Melbourne CBD" in response.text


def test_mocked_google_api_success_with_sensor_match(client: TestClient) -> None:
    sensor = SensorRecord(sensor_id=1, sensor_name="Bourke Street Mall", latitude=-37.8136, longitude=144.9631)
    override_services(
        routes=[make_route("route_with_data", (-37.8136, 144.9631))],
        sensors=[sensor],
        counts={1: count(1, 120)},
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    route = response.json()["routes"][0]
    assert response.status_code == 200
    assert route["pedestrian_data_availability"] == "available"
    assert route["matched_sensor_count"] == 1
    assert route["sensor_coverage_ratio"] == 1
    assert route["sensory_score"] is not None


def test_mocked_google_api_failure(client: TestClient) -> None:
    override_services(routes=[], google_failure=True)
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    assert response.status_code == 502
    assert response.json()["detail"] == "Route provider is unavailable"


def test_route_without_pedestrian_data_returns_warning(client: TestClient) -> None:
    override_services(routes=[make_route("route_no_data", (-37.8183, 144.9671))])
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    route = response.json()["routes"][0]
    assert route["pedestrian_data_availability"] == "unavailable"
    assert "cannot be fully confirmed" in route["warning_message"]
    assert route["sensory_score"] is None


def test_route_with_partial_sensor_coverage(client: TestClient) -> None:
    sensor = SensorRecord(sensor_id=1, sensor_name="Bourke Street Mall", latitude=-37.8136, longitude=144.9631)
    override_services(
        routes=[make_two_segment_route("partial_route")],
        sensors=[sensor],
        counts={1: count(1, 120)},
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    route = response.json()["routes"][0]
    assert response.status_code == 200
    assert route["pedestrian_data_availability"] == "partial"
    assert route["sensor_coverage_ratio"] == 0.5
    assert route["sensory_indicator"] == "Low"
    assert "cannot be fully confirmed" in route["warning_message"]


def test_low_and_high_sensory_classification() -> None:
    service = SensoryScoringService()
    segment_match = SegmentSensorMatch(
        segment_sequence=1,
        matched_sensors=[MatchedSensor(sensor=SensorRecord(1, "Test", -37.8136, 144.9631), distance_m=1, route_point_index=0)],
    )

    low = service.score_route([segment_match], {1: count(1, 120)}, crowd_threshold=3)
    high = service.score_route([segment_match], {1: count(1, 900)}, crowd_threshold=3)

    assert low.sensory_indicator == "Low"
    assert high.sensory_indicator == "High"


def test_crowd_threshold_does_not_change_iteration_one_scoring() -> None:
    service = SensoryScoringService()
    segment_match = SegmentSensorMatch(
        segment_sequence=1,
        matched_sensors=[MatchedSensor(sensor=SensorRecord(1, "Test", -37.8136, 144.9631), distance_m=1, route_point_index=0)],
        distance_m=100,
    )

    strict_preference = service.score_route([segment_match], {1: count(1, 120)}, crowd_threshold=1)
    tolerant_preference = service.score_route([segment_match], {1: count(1, 120)}, crowd_threshold=5)

    assert strict_preference.sensory_score == tolerant_preference.sensory_score
    assert strict_preference.sensory_indicator == tolerant_preference.sensory_indicator


def test_lowest_score_route_is_the_only_recommendation(client: TestClient) -> None:
    low_sensor = SensorRecord(sensor_id=1, sensor_name="Quiet sensor", latitude=-37.8101, longitude=144.9558)
    high_sensor = SensorRecord(sensor_id=2, sensor_name="Busy sensor", latitude=-37.8183, longitude=144.9671)
    override_services(
        routes=[
            make_route("busy_route", (-37.8183, 144.9671), minutes=10),
            make_route("quiet_route", (-37.8101, 144.9558), minutes=14),
        ],
        sensors=[low_sensor, high_sensor],
        counts={1: count(1, 90), 2: count(2, 700)},
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    routes = response.json()["routes"]
    recommended = [route for route in routes if route["is_recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["route_identifier"] == "quiet_route"


def test_tie_breaking_prefers_shorter_travel_time(client: TestClient) -> None:
    sensor_a = SensorRecord(sensor_id=1, sensor_name="Sensor A", latitude=-37.8136, longitude=144.9631)
    sensor_b = SensorRecord(sensor_id=2, sensor_name="Sensor B", latitude=-37.8183, longitude=144.9671)
    override_services(
        routes=[
            make_route("slower_equal_score", (-37.8136, 144.9631), minutes=16),
            make_route("faster_equal_score", (-37.8183, 144.9671), minutes=10),
        ],
        sensors=[sensor_a, sensor_b],
        counts={1: count(1, 120), 2: count(2, 120)},
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    recommended = [route for route in response.json()["routes"] if route["is_recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["route_identifier"] == "faster_equal_score"


def test_all_routes_unavailable_has_no_recommendation(client: TestClient) -> None:
    override_services(
        routes=[
            make_route("missing_a", (-37.8136, 144.9631), minutes=10),
            make_route("missing_b", (-37.8183, 144.9671), minutes=12),
        ],
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    routes = response.json()["routes"]
    assert response.json()["recommended_route_identifier"] is None
    assert [route for route in routes if route["is_recommended"]] == []
    assert all(route["sensory_indicator"] == "Unavailable" for route in routes)


def test_missing_data_route_is_not_treated_as_lowest_score(client: TestClient) -> None:
    high_sensor = SensorRecord(sensor_id=2, sensor_name="Busy sensor", latitude=-37.8183, longitude=144.9671)
    override_services(
        routes=[
            make_route("missing_data_route", (-37.8101, 144.9558), minutes=8),
            make_route("scored_route", (-37.8183, 144.9671), minutes=14),
        ],
        sensors=[high_sensor],
        counts={2: count(2, 700)},
    )
    response = client.post("/api/routes/plan", json=VALID_REQUEST)
    routes = response.json()["routes"]
    recommended = [route for route in routes if route["is_recommended"]]
    missing_route = next(route for route in routes if route["route_identifier"] == "missing_data_route")
    assert len(recommended) == 1
    assert recommended[0]["route_identifier"] == "scored_route"
    assert missing_route["sensory_score"] is None
    assert missing_route["is_recommended"] is False


class BrokenDb:
    def __init__(self) -> None:
        self.rollback_called = False

    def add(self, item) -> None:
        return None

    def flush(self) -> None:
        raise RuntimeError("database write failed")

    def commit(self) -> None:
        raise AssertionError("commit should not be called")

    def rollback(self) -> None:
        self.rollback_called = True


def test_persistence_rolls_back_after_database_failure() -> None:
    db = BrokenDb()
    segment = RouteSegmentResponse(
        segment_sequence=1,
        encoded_polyline=None,
        distance_m=100,
        duration_seconds=60,
        matched_sensor_count=1,
        congestion_level="low",
        sensory_score=0.4,
        data_availability="available",
    )
    response = RouteOptionResponse(
        route_identifier="route_a",
        encoded_polyline=None,
        estimated_travel_minutes=1,
        travel_mode="walking",
        sensory_score=0.4,
        sensory_indicator="Low",
        is_recommended=True,
        pedestrian_data_availability="available",
        data_availability_status="available",
        matched_sensor_count=1,
        sensor_coverage_ratio=1,
        route_segments=[segment],
    )
    result = RouteBuildResult(
        response=response,
        sensor_scores=[
            SegmentSensorScorePersistence(
                segment_sequence=1,
                sensor_id=1,
                count_source="historical",
                observed_at=datetime.now(timezone.utc),
                count_used=120,
                score_contribution=0.4,
            )
        ],
    )

    persist_route_plan(db, RoutePlanningRequest(**VALID_REQUEST), [result])

    assert db.rollback_called is True
