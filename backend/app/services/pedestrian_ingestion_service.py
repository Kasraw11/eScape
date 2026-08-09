from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.pedestrian_count import RealtimePedestrianCount
from app.models.sensor_location import SensorLocation
from app.services.data_freshness_service import ensure_aware


class MelbournePedestrianDataError(RuntimeError):
    pass


MELBOURNE_REALTIME_DATA_SOURCE = (
    "City of Melbourne Open Data: pedestrian-counting-system-past-hour-counts-per-minute"
)


@dataclass
class IngestionStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    invalid: int = 0


@dataclass(frozen=True)
class ValidatedPedestrianReading:
    sensor_id: int
    sensed_at: datetime
    direction_1_count: int | None
    direction_2_count: int | None
    total_count: int
    source_record_id: str


class MelbournePedestrianClient:
    async def fetch_sensor_locations(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=settings.melbourne_pedestrian_api_timeout_seconds)
        records: list[dict[str, Any]] = []
        offset = 0
        try:
            while True:
                response = await http_client.get(
                    settings.melbourne_sensor_locations_api_url,
                    params={"limit": 100, "offset": offset},
                )
                response.raise_for_status()
                payload = response.json()
                page = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(page, list):
                    raise MelbournePedestrianDataError("Melbourne sensor-location response was invalid")
                records.extend(record for record in page if isinstance(record, dict))
                if len(page) < 100:
                    return records
                offset += 100
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise MelbournePedestrianDataError("Melbourne sensor-location request failed") from exc
        finally:
            if owns_client:
                await http_client.aclose()

    async def fetch_latest(
        self,
        client: httpx.AsyncClient | None = None,
        max_records: int = 1000,
    ) -> list[dict[str, Any]]:
        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=settings.melbourne_pedestrian_api_timeout_seconds)
        records: list[dict[str, Any]] = []
        offset = 0
        page_size = min(settings.melbourne_pedestrian_api_limit, 100)
        try:
            while offset < max_records:
                response = await http_client.get(
                    settings.melbourne_pedestrian_api_url,
                    params={
                        "order_by": "sensing_datetime desc",
                        "limit": page_size,
                        "offset": offset,
                        "timezone": "UTC",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                page = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(page, list):
                    raise MelbournePedestrianDataError("Melbourne pedestrian data response was invalid")
                records.extend(record for record in page if isinstance(record, dict))
                if len(page) < page_size:
                    break
                offset += page_size
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise MelbournePedestrianDataError("Melbourne pedestrian data request failed") from exc
        finally:
            if owns_client:
                await http_client.aclose()
        return records


class PedestrianIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(self, raw_records: list[dict[str, Any]]) -> IngestionStats:
        stats = IngestionStats()
        latest_by_sensor: dict[int, ValidatedPedestrianReading] = {}

        for raw_record in raw_records:
            try:
                reading = validate_reading(raw_record)
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue
            existing_latest = latest_by_sensor.get(reading.sensor_id)
            if existing_latest is None or reading.sensed_at > existing_latest.sensed_at:
                latest_by_sensor[reading.sensor_id] = reading
            else:
                stats.skipped += 1

        for reading in latest_by_sensor.values():
            sensor = self.db.get(SensorLocation, reading.sensor_id)
            if sensor is None:
                stats.skipped += 1
                continue
            sensor_updated_at = ensure_aware(getattr(sensor, "last_updated_at", None))
            if sensor_updated_at is None or reading.sensed_at > sensor_updated_at:
                sensor.last_updated_at = reading.sensed_at

            existing = self.db.scalar(
                select(RealtimePedestrianCount).where(
                    RealtimePedestrianCount.sensor_id == reading.sensor_id,
                    RealtimePedestrianCount.sensed_at == reading.sensed_at,
                )
            )
            if existing is None:
                self.db.add(
                    RealtimePedestrianCount(
                        sensor_id=reading.sensor_id,
                        sensed_at=reading.sensed_at,
                        direction_1_count=reading.direction_1_count,
                        direction_2_count=reading.direction_2_count,
                        total_count=reading.total_count,
                        source_record_id=reading.source_record_id,
                        data_source=MELBOURNE_REALTIME_DATA_SOURCE,
                    )
                )
                stats.inserted += 1
                continue

            changed = any(
                getattr(existing, field) != getattr(reading, field)
                for field in ("direction_1_count", "direction_2_count", "total_count", "source_record_id")
            )
            changed = changed or getattr(existing, "data_source", None) != MELBOURNE_REALTIME_DATA_SOURCE
            if changed:
                existing.direction_1_count = reading.direction_1_count
                existing.direction_2_count = reading.direction_2_count
                existing.total_count = reading.total_count
                existing.source_record_id = reading.source_record_id
                existing.data_source = MELBOURNE_REALTIME_DATA_SOURCE
                stats.updated += 1
            else:
                stats.skipped += 1

        return stats

    def ingest_sensor_locations(self, raw_records: list[dict[str, Any]]) -> IngestionStats:
        stats = IngestionStats()
        for record in raw_records:
            try:
                values = validate_sensor_location(record)
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue

            sensor = self.db.get(SensorLocation, values["sensor_id"])
            if sensor is None:
                self.db.add(SensorLocation(**values))
                stats.inserted += 1
                continue

            changed = False
            for field, value in values.items():
                if field != "sensor_id" and getattr(sensor, field) != value:
                    setattr(sensor, field, value)
                    changed = True
            if changed:
                stats.updated += 1
            else:
                stats.skipped += 1
        return stats


def validate_sensor_location(record: dict[str, Any]) -> dict[str, Any]:
    sensor_id = int(record["location_id"])
    latitude = Decimal(str(record["latitude"]))
    longitude = Decimal(str(record["longitude"]))
    if not Decimal("-90") <= latitude <= Decimal("90"):
        raise ValueError("Latitude out of range")
    if not Decimal("-180") <= longitude <= Decimal("180"):
        raise ValueError("Longitude out of range")

    installation_date = record.get("installation_date")
    parsed_date = date.fromisoformat(str(installation_date)[:10]) if installation_date else None
    return {
        "sensor_id": sensor_id,
        "sensor_name": str(record.get("sensor_name") or record.get("sensor_description") or f"Sensor {sensor_id}"),
        "description": record.get("sensor_description"),
        "location_name": record.get("sensor_name"),
        "location_type": record.get("location_type"),
        "latitude": latitude,
        "longitude": longitude,
        "installation_date": parsed_date,
        "status": str(record.get("status") or "unknown"),
        "direction_1": record.get("direction_1"),
        "direction_2": record.get("direction_2"),
        "source": "City of Melbourne Open Data",
        "last_updated_at": None,
    }


def validate_reading(record: dict[str, Any]) -> ValidatedPedestrianReading:
    sensor_id = int(record["location_id"])
    timestamp_value = record.get("sensing_datetime") or record.get("sensing_date_time")
    if not timestamp_value:
        raise ValueError("Missing sensing timestamp")
    sensed_at = ensure_aware(datetime.fromisoformat(str(timestamp_value).replace("Z", "+00:00")))
    if sensed_at is None:
        raise ValueError("Invalid sensing timestamp")

    def optional_count(*keys: str) -> int | None:
        value = next((record.get(key) for key in keys if record.get(key) not in (None, "")), None)
        return int(value) if value is not None else None

    direction_1 = optional_count("direction_1", "direction_1_count")
    direction_2 = optional_count("direction_2", "direction_2_count")
    total = optional_count("total_of_directions", "pedestriancount", "total_count")
    if total is None:
        if direction_1 is None and direction_2 is None:
            raise ValueError("Missing pedestrian counts")
        total = (direction_1 or 0) + (direction_2 or 0)
    if any(value is not None and value < 0 for value in (direction_1, direction_2, total)):
        raise ValueError("Pedestrian counts cannot be negative")

    source_record_id = str(record.get("id") or record.get("recordid") or f"{sensor_id}:{sensed_at.isoformat()}")
    return ValidatedPedestrianReading(
        sensor_id=sensor_id,
        sensed_at=sensed_at.astimezone(timezone.utc),
        direction_1_count=direction_1,
        direction_2_count=direction_2,
        total_count=total,
        source_record_id=source_record_id,
    )
