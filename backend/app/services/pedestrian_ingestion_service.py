from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    async def fetch_latest(self, client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=settings.melbourne_pedestrian_api_timeout_seconds)
        try:
            response = await http_client.get(
                settings.melbourne_pedestrian_api_url,
                params={
                    "order_by": "sensing_datetime desc",
                    "limit": settings.melbourne_pedestrian_api_limit,
                    "timezone": "UTC",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise MelbournePedestrianDataError("Melbourne pedestrian data request failed") from exc
        finally:
            if owns_client:
                await http_client.aclose()

        records = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise MelbournePedestrianDataError("Melbourne pedestrian data response was invalid")
        return records

    async def fetch_records(self, max_records: int = 1000) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        offset = 0
        limit = settings.melbourne_pedestrian_api_limit

        async with httpx.AsyncClient(timeout=settings.melbourne_pedestrian_api_timeout_seconds) as client:
            while len(records) < max_records:
                batch_limit = min(limit, max_records - len(records))
                response = await client.get(
                    settings.melbourne_pedestrian_api_url,
                    params={
                        "order_by": "sensing_datetime desc",
                        "limit": batch_limit,
                        "offset": offset,
                        "timezone": "UTC",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                batch = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(batch, list):
                    raise MelbournePedestrianDataError("Melbourne pedestrian data response was invalid")
                records.extend(batch)

                total_count = payload.get("total_count", offset + len(batch))
                offset += len(batch)
                if not batch or offset >= total_count:
                    break

        return records


class PedestrianIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(self, raw_records: list[dict[str, Any]]) -> IngestionStats:
        stats = IngestionStats()
        readings: list[ValidatedPedestrianReading] = []

        for raw_record in raw_records:
            try:
                reading = validate_reading(raw_record)
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue
            readings.append(reading)

        if not readings:
            return stats

        sensor_ids = sorted({reading.sensor_id for reading in readings})
        valid_sensor_ids = set(
            self.db.scalars(
                select(SensorLocation.sensor_id).where(SensorLocation.sensor_id.in_(sensor_ids))
            ).all()
        )
        existing_keys = {
            (int(sensor_id), ensure_aware(sensed_at))
            for sensor_id, sensed_at in self.db.execute(
                select(RealtimePedestrianCount.sensor_id, RealtimePedestrianCount.sensed_at).where(
                    RealtimePedestrianCount.sensor_id.in_(sensor_ids)
                )
            ).all()
        }

        for reading in readings:
            if reading.sensor_id not in valid_sensor_ids:
                stats.skipped += 1
                continue

            existing_key = (reading.sensor_id, ensure_aware(reading.sensed_at))
            if existing_key in existing_keys:
                stats.skipped += 1
                continue

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
            existing_keys.add(existing_key)
            stats.inserted += 1

        return stats


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
