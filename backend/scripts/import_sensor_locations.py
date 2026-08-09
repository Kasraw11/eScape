from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal
from app.models.sensor_location import SensorLocation


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SENSOR_LOCATION_DATA_SOURCE = "City of Melbourne Open Data: pedestrian-counting-system-sensor-locations"


@dataclass
class ImportStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    invalid: int = 0


async def fetch_sensor_locations() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    limit = settings.melbourne_pedestrian_api_limit

    async with httpx.AsyncClient(timeout=settings.melbourne_pedestrian_api_timeout_seconds) as client:
        while True:
            response = await client.get(
                settings.melbourne_sensor_locations_api_url,
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list):
                raise RuntimeError("Sensor location response was invalid")
            records.extend(results)

            total_count = payload.get("total_count", offset + len(results))
            offset += len(results)
            if not results or offset >= total_count:
                break

    return records


def parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid coordinate value") from exc


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    sensor_id = int(record["location_id"])
    latitude = parse_decimal(record["latitude"])
    longitude = parse_decimal(record["longitude"])
    if not Decimal("-90") <= latitude <= Decimal("90"):
        raise ValueError("Latitude out of range")
    if not Decimal("-180") <= longitude <= Decimal("180"):
        raise ValueError("Longitude out of range")

    return {
        "sensor_id": sensor_id,
        "sensor_name": str(record.get("sensor_name") or record.get("sensor_description") or sensor_id),
        "description": record.get("sensor_description"),
        "location_name": record.get("sensor_description"),
        "location_type": record.get("location_type"),
        "latitude": latitude,
        "longitude": longitude,
        "installation_date": parse_date(record.get("installation_date")),
        "status": str(record.get("status") or "unknown"),
        "direction_1": record.get("direction_1"),
        "direction_2": record.get("direction_2"),
        "source": SENSOR_LOCATION_DATA_SOURCE,
    }


def upsert_sensor(db: Session, values: dict[str, Any], stats: ImportStats) -> None:
    sensor = db.get(SensorLocation, values["sensor_id"])
    if sensor is None:
        db.add(SensorLocation(**values))
        stats.inserted += 1
        return

    changed = False
    for key, value in values.items():
        if getattr(sensor, key) != value:
            setattr(sensor, key, value)
            changed = True
    if changed:
        stats.updated += 1
    else:
        stats.skipped += 1


async def run() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    raw_records = await fetch_sensor_locations()
    stats = ImportStats()
    with SessionLocal() as db:
        for record in raw_records:
            try:
                upsert_sensor(db, validate_record(record), stats)
            except Exception:
                stats.invalid += 1
        db.commit()

    logger.info(
        "Sensor location import completed: inserted=%d updated=%d skipped=%d invalid=%d",
        stats.inserted,
        stats.updated,
        stats.skipped,
        stats.invalid,
    )


if __name__ == "__main__":
    asyncio.run(run())
