from fastapi.testclient import TestClient

from app.main import app
from datetime import date, datetime

from app.core.crowd import CrowdLevel
from app.schemas.crowd import PedestrianCount, SensorLocation, SensoryRefuge
from app.services.city_of_melbourne import get_city_client


class FakeCityClient:
    async def fetch_sensor_locations(self) -> list[SensorLocation]:
        return [
            SensorLocation(
                sensor_id=5,
                sensor_name="PriNW_T",
                sensor_description="Princes Bridge",
                latitude=-37.81874249,
                longitude=144.96787656,
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
                direction_1=140,
                direction_2=120,
                total_of_directions=260,
                crowd_level=CrowdLevel.MEDIUM,
            )
        ]

    async def fetch_sensory_refuges(self) -> list[SensoryRefuge]:
        return [
            SensoryRefuge(
                name="Treasury Gardens",
                theme="Leisure/Recreation",
                sub_theme="Informal Outdoor Facility (Park/Garden/Reserve)",
                latitude=-37.8149,
                longitude=144.9741,
                data_note="Opening hours and sensory conditions are not available in this dataset.",
            )
        ]


def test_sensor_locations_endpoint_returns_validated_records() -> None:
    app.dependency_overrides[get_city_client] = lambda: FakeCityClient()
    client = TestClient(app)

    response = client.get("/api/crowd/sensor-locations")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["sensors"][0]["sensor_id"] == 5


def test_latest_counts_endpoint_returns_summary() -> None:
    app.dependency_overrides[get_city_client] = lambda: FakeCityClient()
    client = TestClient(app)

    response = client.get("/api/crowd/latest-counts")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["summary"]["medium_count"] == 1
    assert body["readings"][0]["crowd_level"] == "medium"


def test_nearby_refuges_endpoint_returns_ranked_refuges() -> None:
    app.dependency_overrides[get_city_client] = lambda: FakeCityClient()
    client = TestClient(app)

    response = client.get("/api/crowd/refuges/nearby?latitude=-37.815&longitude=144.97")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["refuges"][0]["name"] == "Treasury Gardens"
    assert body["refuges"][0]["distance_m"] is not None
