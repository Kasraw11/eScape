from typing import Any

import httpx
from pydantic import ValidationError

from app.core.crowd import CrowdLevel, classify_crowd_count
from app.core.config import get_settings
from app.schemas.crowd import LiveCrowdSummary, PedestrianCount, SensorLocation, SensoryRefuge


class CityOfMelbourneClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_sensor_locations(self, limit: int = 100) -> list[SensorLocation]:
        records: list[SensorLocation] = []
        offset = 0

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            while True:
                response = await client.get(
                    "/api/explore/v2.1/catalog/datasets/"
                    "pedestrian-counting-system-sensor-locations/records",
                    params={
                        "limit": limit,
                        "offset": offset,
                        "select": (
                            "location_id,sensor_description,sensor_name,"
                            "installation_date,location_type,status,"
                            "direction_1,direction_2,latitude,longitude"
                        ),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results")

                if not isinstance(results, list):
                    return records

                for raw_record in results:
                    sensor = self._parse_sensor_location(raw_record)
                    if sensor is not None:
                        records.append(sensor)

                if len(results) < limit:
                    return records

                offset += limit

    async def fetch_latest_pedestrian_counts(
        self,
        limit: int = 100,
        max_records: int = 1000,
    ) -> list[PedestrianCount]:
        latest_by_location: dict[int, PedestrianCount] = {}
        offset = 0

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            while offset < max_records:
                response = await client.get(
                    "/api/explore/v2.1/catalog/datasets/"
                    "pedestrian-counting-system-past-hour-counts-per-minute/records",
                    params={
                        "limit": limit,
                        "offset": offset,
                        "order_by": "sensing_datetime desc",
                        "select": (
                            "location_id,sensing_datetime,sensing_date,"
                            "sensing_time,direction_1,direction_2,total_of_directions"
                        ),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results")

                if not isinstance(results, list):
                    return self._sort_latest_counts(latest_by_location)

                for raw_record in results:
                    count = self._parse_pedestrian_count(raw_record)
                    if count is None:
                        continue

                    existing = latest_by_location.get(count.location_id)
                    if existing is None or count.sensing_datetime > existing.sensing_datetime:
                        latest_by_location[count.location_id] = count

                if len(results) < limit:
                    return self._sort_latest_counts(latest_by_location)

                offset += limit

        return self._sort_latest_counts(latest_by_location)

    async def fetch_recent_hourly_counts_fallback(
        self,
        limit: int = 100,
        max_records: int = 1000,
    ) -> list[PedestrianCount]:
        latest_by_location: dict[int, PedestrianCount] = {}
        offset = 0

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            while offset < max_records:
                response = await client.get(
                    "/api/explore/v2.1/catalog/datasets/"
                    "pedestrian-counting-system-monthly-counts-per-hour/records",
                    params={
                        "limit": limit,
                        "offset": offset,
                        "order_by": "sensing_date desc,hourday desc",
                        "select": (
                            "location_id,sensing_date,hourday,"
                            "direction_1,direction_2,pedestriancount"
                        ),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results")

                if not isinstance(results, list):
                    return self._sort_latest_counts(latest_by_location)

                for raw_record in results:
                    count = self._parse_hourly_count(raw_record)
                    if count is None:
                        continue

                    existing = latest_by_location.get(count.location_id)
                    if existing is None or count.sensing_datetime > existing.sensing_datetime:
                        latest_by_location[count.location_id] = count

                if len(results) < limit:
                    return self._sort_latest_counts(latest_by_location)

                offset += limit

        return self._sort_latest_counts(latest_by_location)

    async def fetch_sensory_refuges(self, limit: int = 100, max_records: int = 1000) -> list[SensoryRefuge]:
        records: list[SensoryRefuge] = []
        offset = 0

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            while offset < max_records:
                response = await client.get(
                    "/api/explore/v2.1/catalog/datasets/"
                    "landmarks-and-places-of-interest-including-schools-theatres-health-services-spor/records",
                    params={
                        "limit": limit,
                        "offset": offset,
                        "select": "theme,sub_theme,feature_name,co_ordinates",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results")

                if not isinstance(results, list):
                    return records

                for raw_record in results:
                    refuge = self._parse_sensory_refuge(raw_record)
                    if refuge is not None and is_refuge_candidate(refuge):
                        records.append(refuge)

                if len(results) < limit:
                    return records

                offset += limit

        return records

    def _parse_sensor_location(self, raw_record: Any) -> SensorLocation | None:
        if not isinstance(raw_record, dict):
            return None

        data = {
            "sensor_id": raw_record.get("location_id"),
            "location_id": raw_record.get("location_id"),
            "sensor_name": raw_record.get("sensor_name"),
            "sensor_description": raw_record.get("sensor_description"),
            "installation_date": raw_record.get("installation_date"),
            "location_type": raw_record.get("location_type"),
            "status": raw_record.get("status"),
            "direction_1": raw_record.get("direction_1"),
            "direction_2": raw_record.get("direction_2"),
            "latitude": raw_record.get("latitude"),
            "longitude": raw_record.get("longitude"),
        }

        try:
            return SensorLocation.model_validate(data)
        except ValidationError:
            return None

    def _parse_pedestrian_count(self, raw_record: Any) -> PedestrianCount | None:
        if not isinstance(raw_record, dict):
            return None

        total = raw_record.get("total_of_directions")
        if not isinstance(total, int):
            return None

        data = {
            "location_id": raw_record.get("location_id"),
            "sensing_datetime": raw_record.get("sensing_datetime"),
            "sensing_date": raw_record.get("sensing_date"),
            "sensing_time": raw_record.get("sensing_time"),
            "direction_1": raw_record.get("direction_1"),
            "direction_2": raw_record.get("direction_2"),
            "total_of_directions": total,
            "crowd_level": classify_crowd_count(total),
        }

        try:
            return PedestrianCount.model_validate(data)
        except ValidationError:
            return None

    def _parse_hourly_count(self, raw_record: Any) -> PedestrianCount | None:
        if not isinstance(raw_record, dict):
            return None

        total = raw_record.get("pedestriancount")
        hour = raw_record.get("hourday")
        sensing_date = raw_record.get("sensing_date")

        if not isinstance(total, int) or not isinstance(hour, int) or not isinstance(sensing_date, str):
            return None

        data = {
            "location_id": raw_record.get("location_id"),
            "sensing_datetime": f"{sensing_date}T{hour:02d}:00:00+10:00",
            "sensing_date": sensing_date,
            "sensing_time": f"{hour:02d}:00",
            "direction_1": raw_record.get("direction_1") or 0,
            "direction_2": raw_record.get("direction_2") or 0,
            "total_of_directions": total,
            "crowd_level": classify_crowd_count(total),
        }

        try:
            return PedestrianCount.model_validate(data)
        except ValidationError:
            return None

    def _parse_sensory_refuge(self, raw_record: Any) -> SensoryRefuge | None:
        if not isinstance(raw_record, dict):
            return None

        coordinates = raw_record.get("co_ordinates")
        if isinstance(coordinates, dict):
            latitude = coordinates.get("lat")
            longitude = coordinates.get("lon")
        elif isinstance(coordinates, list) and len(coordinates) == 2:
            latitude = coordinates[0]
            longitude = coordinates[1]
        else:
            return None

        if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
            return None

        data = {
            "name": raw_record.get("feature_name"),
            "theme": raw_record.get("theme"),
            "sub_theme": raw_record.get("sub_theme"),
            "latitude": latitude,
            "longitude": longitude,
            "data_note": "Opening hours and sensory conditions are not available in this dataset.",
        }

        try:
            return SensoryRefuge.model_validate(data)
        except ValidationError:
            return None

    def _sort_latest_counts(
        self,
        latest_by_location: dict[int, PedestrianCount],
    ) -> list[PedestrianCount]:
        return sorted(
            latest_by_location.values(),
            key=lambda count: (count.crowd_level, -count.total_of_directions),
        )


def summarise_live_counts(readings: list[PedestrianCount]) -> LiveCrowdSummary:
    return LiveCrowdSummary(
        total_readings=len(readings),
        low_count=sum(1 for reading in readings if reading.crowd_level == CrowdLevel.LOW),
        medium_count=sum(1 for reading in readings if reading.crowd_level == CrowdLevel.MEDIUM),
        high_count=sum(1 for reading in readings if reading.crowd_level == CrowdLevel.HIGH),
    )


def is_refuge_candidate(refuge: SensoryRefuge) -> bool:
    theme = (refuge.theme or "").lower()
    sub_theme = (refuge.sub_theme or "").lower()

    if "carpark" in sub_theme:
        return False

    return (
        "park/garden/reserve" in sub_theme
        or "public buildings" in sub_theme
        or "library" in sub_theme
        or "community" in theme
    )


def find_nearby_refuges(
    refuges: list[SensoryRefuge],
    latitude: float,
    longitude: float,
    limit: int,
) -> list[SensoryRefuge]:
    from app.core.validation import Coordinate
    from app.services.routing_service import haversine_m

    origin = Coordinate(latitude=latitude, longitude=longitude)
    ranked = sorted(
        refuges,
        key=lambda refuge: haversine_m(
            origin,
            Coordinate(latitude=refuge.latitude, longitude=refuge.longitude),
        ),
    )

    return [
        refuge.model_copy(
            update={
                "distance_m": round(
                    haversine_m(
                        origin,
                        Coordinate(latitude=refuge.latitude, longitude=refuge.longitude),
                    )
                )
            }
        )
        for refuge in ranked[:limit]
    ]


def get_city_client() -> CityOfMelbourneClient:
    settings = get_settings()
    return CityOfMelbourneClient(
        base_url=settings.city_of_melbourne_base_url,
        timeout_seconds=settings.external_api_timeout_seconds,
    )
