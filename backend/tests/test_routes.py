from fastapi.testclient import TestClient

from app.core.crowd import CrowdLevel
from app.main import app
from app.schemas.crowd import PedestrianCount, SensorLocation
from app.services.city_of_melbourne import get_city_client
from app.services.openrouteservice_client import get_openrouteservice_client, get_osm_route_client
from datetime import date, datetime


client = TestClient(app)


class FakeCityClient:
    async def fetch_sensor_locations(self) -> list[SensorLocation]:
        return [
            SensorLocation(
                sensor_id=5,
                sensor_name="PriNW_T",
                sensor_description="Princes Bridge",
                latitude=-37.8166,
                longitude=144.9658,
                status="A",
                location_type="Outdoor",
            )
        ]

    async def fetch_latest_pedestrian_counts(self) -> list[PedestrianCount]:
        return [
            PedestrianCount(
                location_id=5,
                sensing_datetime=datetime.fromisoformat("2026-06-23T03:41:00+00:00"),
                sensing_date=date.fromisoformat("2026-06-23"),
                sensing_time="13:41",
                direction_1=450,
                direction_2=360,
                total_of_directions=810,
                crowd_level=CrowdLevel.HIGH,
            )
        ]


class FakeOpenRouteServiceClient:
    async def compute_walking_routes(self, payload):
        return []


class FakeOsmRouteServiceClient:
    async def compute_walking_routes(self, payload):
        return []


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_route_plan_validates_basic_payload() -> None:
    app.dependency_overrides[get_city_client] = lambda: FakeCityClient()
    app.dependency_overrides[get_openrouteservice_client] = lambda: FakeOpenRouteServiceClient()
    app.dependency_overrides[get_osm_route_client] = lambda: FakeOsmRouteServiceClient()
    response = client.post(
        "/api/routes/plan",
        json={
            "origin": {"label": "Flinders Street Station"},
            "destination": {"label": "State Library Victoria"},
            "crowd_threshold": "low",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["requested_threshold"] == "low"
    assert len(body["routes"]) == 3
    assert any(route["is_recommended"] for route in body["routes"])
    assert any(route["matched_sensor_count"] > 0 for route in body["routes"])


def test_route_plan_rejects_invalid_threshold() -> None:
    app.dependency_overrides[get_city_client] = lambda: FakeCityClient()
    app.dependency_overrides[get_openrouteservice_client] = lambda: FakeOpenRouteServiceClient()
    app.dependency_overrides[get_osm_route_client] = lambda: FakeOsmRouteServiceClient()
    response = client.post(
        "/api/routes/plan",
        json={
            "origin": {"label": "Flinders Street Station"},
            "destination": {"label": "State Library Victoria"},
            "crowd_threshold": "extreme",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422
