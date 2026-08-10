from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.repositories.pedestrian_repository import PedestrianRepository


SENSOR_LOCATIONS_URL = (
    "https://data.melbourne.vic.gov.au/"
    "api/explore/v2.1/catalog/datasets/"
    "pedestrian-counting-system-sensor-locations/records"
)

RECENT_COUNTS_URL = (
    "https://data.melbourne.vic.gov.au/"
    "api/explore/v2.1/catalog/datasets/"
    "pedestrian-counting-system-past-hour-counts-per-minute/records"
)


@dataclass(frozen=True)
class LivePedestrianSensor:
    sensor_id: int
    sensor_name: str
    latitude: float
    longitude: float
    pedestrian_count: int | None


class MelbournePedestrianService:
    """
    Fetches pedestrian sensor information directly
    from the City of Melbourne Open Data API.

    It can also save the fetched data into the
    eScape database when a repository is supplied.
    """

    def __init__(
        self,
        repository: PedestrianRepository | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.repository = repository
        self.timeout_seconds = timeout_seconds

    async def get_sensor_locations(
        self,
    ) -> list[LivePedestrianSensor]:
        """
        Fetch sensor locations and attach the most
        recent pedestrian count when available.
        """

        locations = await self._fetch_locations()
        recent_counts = await self._fetch_recent_counts()

        sensors: list[LivePedestrianSensor] = []

        for location in locations:
            sensors.append(
                LivePedestrianSensor(
                    sensor_id=location["sensor_id"],
                    sensor_name=location["sensor_name"],
                    latitude=location["latitude"],
                    longitude=location["longitude"],
                    pedestrian_count=recent_counts.get(
                        location["sensor_id"]
                    ),
                )
            )

        return sensors

    async def sync_to_database(self) -> dict[str, int]:
        """
        Fetch live pedestrian data and save it into
        the database.

        Returns a small summary showing how many
        sensors and realtime readings were processed.
        """

        if self.repository is None:
            raise RuntimeError(
                "A PedestrianRepository is required "
                "to sync pedestrian data."
            )

        locations = await self._fetch_locations()
        recent_readings = await self._fetch_recent_readings()

        sensor_count = 0
        reading_count = 0

        try:
            # Save or update sensor locations first.
            for location in locations:
                self.repository.upsert_sensor(
                    sensor_id=location["sensor_id"],
                    sensor_name=location["sensor_name"],
                    latitude=location["latitude"],
                    longitude=location["longitude"],
                    status="active",
                    source="City of Melbourne",
                    last_updated_at=datetime.now(
                        timezone.utc
                    ),
                )

                sensor_count += 1

            # Flush sensor records before inserting
            # realtime readings that reference them.
            if self.repository.db is not None:
                self.repository.db.flush()

            # Save recent pedestrian readings.
            for reading in recent_readings:
                inserted = (
                    self.repository.add_realtime_count(
                        sensor_id=reading["sensor_id"],
                        sensed_at=reading["sensed_at"],
                        total_count=reading["total_count"],
                        direction_1_count=reading[
                            "direction_1_count"
                        ],
                        direction_2_count=reading[
                            "direction_2_count"
                        ],
                        source_record_id=reading[
                            "source_record_id"
                        ],
                        data_source="City of Melbourne",
                    )
                )

                if inserted:
                    reading_count += 1

            self.repository.commit()

        except Exception:
            self.repository.rollback()
            raise

        return {
            "sensors_processed": sensor_count,
            "readings_inserted": reading_count,
        }

    async def _fetch_locations(
        self,
    ) -> list[dict]:
        """
        Fetch all pedestrian sensor locations.

        The City of Melbourne API returns records in
        pages, so we continue until all locations have
        been retrieved.
        """

        locations: list[dict] = []

        limit = 100
        offset = 0

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds
        ) as client:

            while True:
                params = {
                    "limit": limit,
                    "offset": offset,
                }

                response = await client.get(
                    SENSOR_LOCATIONS_URL,
                    params=params,
                )

                response.raise_for_status()
                payload = response.json()

                results = payload.get("results", [])

                if not results:
                    break

                for item in results:
                    sensor_id = item.get("location_id")
                    location = item.get("location")

                    if sensor_id is None or not location:
                        continue

                    latitude = location.get("lat")
                    longitude = location.get("lon")

                    if latitude is None or longitude is None:
                        continue

                    locations.append(
                        {
                            "sensor_id": int(sensor_id),

                            "sensor_name": (
                                item.get("sensor_description")
                                or item.get("sensor_name")
                                or f"Sensor {sensor_id}"
                            ),

                            "latitude": float(latitude),
                            "longitude": float(longitude),
                        }
                    )

                offset += limit

                total_count = payload.get(
                    "total_count",
                    0,
                )

                if offset >= total_count:
                    break
                    
        return locations
    async def _fetch_recent_counts(
        self,
    ) -> dict[int, int]:
        """
        Return only the newest count for each sensor.

        This method is used by the temporary API
        preview endpoint.
        """

        readings = await self._fetch_recent_readings()

        counts: dict[int, int] = {}
        
        for reading in readings:
            sensor_id = reading["sensor_id"]

            if sensor_id not in counts:
                counts[sensor_id] = reading[
                    "total_count"
                ]

        return counts

    async def _fetch_recent_readings(
        self,
    ) -> list[dict]:
        """
        Fetch recent pedestrian readings with their
        timestamps so they can be stored in the
        realtime pedestrian table.
        """

        params = {
            "limit": 100,
            "order_by": "sensing_datetime desc",
        }

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds
        ) as client:
            response = await client.get(
                RECENT_COUNTS_URL,
                params=params,
            )

            response.raise_for_status()
            payload = response.json()

        readings: list[dict] = []
        
        for item in payload.get("results", []):
            sensor_id = item.get("location_id")
            sensing_datetime = item.get(
                "sensing_datetime"
            )
            total_count = item.get(
                "total_of_directions"
            )

            if (
                sensor_id is None
                or sensing_datetime is None
                or total_count is None
            ):
                continue

            try:
                sensed_at = datetime.fromisoformat(
                    sensing_datetime.replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError:
                continue

            readings.append(
                {
                    "sensor_id": int(sensor_id),
                    "sensed_at": sensed_at,
                    "total_count": int(total_count),
                    "direction_1_count": (
                        int(item["direction_1"])
                        if item.get("direction_1")
                        is not None
                        else None
                    ),
                    "direction_2_count": (
                        int(item["direction_2"])
                        if item.get("direction_2")
                        is not None
                        else None
                    ),
                    "source_record_id": (
                        str(item.get("id"))
                        if item.get("id")
                        is not None
                        else None
                    ),
                }
            )
        
        return readings