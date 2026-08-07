import httpx
import pytest
import respx

from app.services.city_of_melbourne import CityOfMelbourneClient


@pytest.mark.anyio
async def test_fetch_sensor_locations_validates_external_records() -> None:
    client = CityOfMelbourneClient(
        base_url="https://data.melbourne.vic.gov.au",
        timeout_seconds=5,
    )

    with respx.mock:
        respx.get(
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/"
            "datasets/pedestrian-counting-system-sensor-locations/records"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "location_id": 5,
                            "sensor_description": "Princes Bridge",
                            "sensor_name": "PriNW_T",
                            "installation_date": "2009-03-26",
                            "location_type": "Outdoor",
                            "status": "A",
                            "direction_1": "North",
                            "direction_2": "South",
                            "latitude": -37.81874249,
                            "longitude": 144.96787656,
                        },
                        {
                            "location_id": None,
                            "sensor_name": "Broken",
                            "status": "A",
                            "latitude": "not-a-number",
                            "longitude": 144.96787656,
                        },
                    ]
                },
            )
        )

        sensors = await client.fetch_sensor_locations()

    assert len(sensors) == 1
    assert sensors[0].sensor_id == 5
    assert sensors[0].sensor_name == "PriNW_T"


@pytest.mark.anyio
async def test_fetch_latest_pedestrian_counts_keeps_latest_valid_record_per_location() -> None:
    client = CityOfMelbourneClient(
        base_url="https://data.melbourne.vic.gov.au",
        timeout_seconds=5,
    )

    with respx.mock:
        respx.get(
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/"
            "datasets/pedestrian-counting-system-past-hour-counts-per-minute/records"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "location_id": 5,
                            "sensing_datetime": "2026-06-23T03:41:00+00:00",
                            "sensing_date": "2026-06-23",
                            "sensing_time": "13:41",
                            "direction_1": 140,
                            "direction_2": 120,
                            "total_of_directions": 260,
                        },
                        {
                            "location_id": 5,
                            "sensing_datetime": "2026-06-23T03:40:00+00:00",
                            "sensing_date": "2026-06-23",
                            "sensing_time": "13:40",
                            "direction_1": 10,
                            "direction_2": 12,
                            "total_of_directions": 22,
                        },
                        {
                            "location_id": 9,
                            "sensing_datetime": "2026-06-23T03:41:00+00:00",
                            "sensing_date": "2026-06-23",
                            "sensing_time": "13:41",
                            "direction_1": 800,
                            "direction_2": 100,
                            "total_of_directions": 900,
                        },
                        {
                            "location_id": 10,
                            "sensing_datetime": "not-a-date",
                            "sensing_date": "2026-06-23",
                            "sensing_time": "13:41",
                            "direction_1": 1,
                            "direction_2": 2,
                            "total_of_directions": 3,
                        },
                    ]
                },
            )
        )

        readings = await client.fetch_latest_pedestrian_counts()

    assert len(readings) == 2
    assert {reading.location_id for reading in readings} == {5, 9}
    assert next(reading for reading in readings if reading.location_id == 5).total_of_directions == 260
    assert next(reading for reading in readings if reading.location_id == 9).crowd_level == "high"


@pytest.mark.anyio
async def test_fetch_sensory_refuges_validates_coordinates() -> None:
    client = CityOfMelbourneClient(
        base_url="https://data.melbourne.vic.gov.au",
        timeout_seconds=5,
    )

    with respx.mock:
        respx.get(
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/"
            "datasets/landmarks-and-places-of-interest-including-schools-theatres-health-services-spor/records"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "theme": "Leisure/Recreation",
                            "sub_theme": "Informal Outdoor Facility (Park/Garden/Reserve)",
                            "feature_name": "Treasury Gardens",
                            "co_ordinates": [-37.8149, 144.9741],
                        },
                        {
                            "theme": "Leisure/Recreation",
                            "sub_theme": "Informal Outdoor Facility (Park/Garden/Reserve)",
                            "feature_name": "Broken Park",
                            "co_ordinates": ["bad", 144.9741],
                        },
                    ]
                },
            )
        )

        refuges = await client.fetch_sensory_refuges()

    assert len(refuges) == 1
    assert refuges[0].name == "Treasury Gardens"
