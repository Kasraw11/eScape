from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.pedestrian_count import HistoricalPedestrianCount
from app.models.sensor_location import SensorLocation


DEFAULT_INPUT_PATH = REPO_ROOT / "database" / "raw" / "pedestrian_counts_sample.csv"


@dataclass
class ImportStats:
    sensors_inserted: int = 0
    sensors_updated: int = 0
    counts_inserted: int = 0
    counts_skipped: int = 0
    invalid_rows: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import sample Melbourne pedestrian sensor counts.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Path to a local CSV or JSON file.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("JSON input must contain a list of row objects")
        return data

    raise ValueError("Input file must be CSV or JSON")


def parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid decimal value") from exc


def parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid integer value") from exc


def parse_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return parse_int(value)


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    latitude = parse_decimal(row["latitude"])
    longitude = parse_decimal(row["longitude"])
    if not Decimal("-90") <= latitude <= Decimal("90"):
        raise ValueError("Latitude out of range")
    if not Decimal("-180") <= longitude <= Decimal("180"):
        raise ValueError("Longitude out of range")

    hour_of_day = parse_int(row["hour_of_day"])
    if not 0 <= hour_of_day <= 23:
        raise ValueError("Hour of day out of range")

    direction_1_count = parse_optional_int(row.get("direction_1_count"))
    direction_2_count = parse_optional_int(row.get("direction_2_count"))
    total_count = parse_int(row["total_count"])
    counts = [value for value in (direction_1_count, direction_2_count, total_count) if value is not None]
    if any(value < 0 for value in counts):
        raise ValueError("Counts cannot be negative")

    return {
        "sensor_id": parse_int(row["sensor_id"]),
        "sensor_name": row["sensor_name"],
        "description": row.get("description") or None,
        "location_name": row.get("location_name") or None,
        "location_type": row.get("location_type") or None,
        "latitude": latitude,
        "longitude": longitude,
        "installation_date": parse_date(row.get("installation_date")),
        "status": row["status"],
        "direction_1": row.get("direction_1") or None,
        "direction_2": row.get("direction_2") or None,
        "source": row.get("source") or None,
        "last_updated_at": parse_datetime(row.get("last_updated_at")),
        "sensing_date": parse_date(row["sensing_date"]),
        "hour_of_day": hour_of_day,
        "direction_1_count": direction_1_count,
        "direction_2_count": direction_2_count,
        "total_count": total_count,
        "source_record_id": row.get("source_record_id") or None,
    }


def upsert_sensor(db: Session, row: dict[str, Any], stats: ImportStats) -> SensorLocation:
    sensor = db.get(SensorLocation, row["sensor_id"])
    sensor_values = {
        "sensor_name": row["sensor_name"],
        "description": row["description"],
        "location_name": row["location_name"],
        "location_type": row["location_type"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "installation_date": row["installation_date"],
        "status": row["status"],
        "direction_1": row["direction_1"],
        "direction_2": row["direction_2"],
        "source": row["source"],
        "last_updated_at": row["last_updated_at"],
    }

    if sensor is None:
        sensor = SensorLocation(sensor_id=row["sensor_id"], **sensor_values)
        db.add(sensor)
        stats.sensors_inserted += 1
        return sensor

    changed = False
    for key, value in sensor_values.items():
        if getattr(sensor, key) != value:
            setattr(sensor, key, value)
            changed = True

    if changed:
        stats.sensors_updated += 1
    return sensor


def insert_count_if_missing(db: Session, row: dict[str, Any], stats: ImportStats) -> None:
    existing = db.scalar(
        select(HistoricalPedestrianCount).where(
            HistoricalPedestrianCount.sensor_id == row["sensor_id"],
            HistoricalPedestrianCount.sensing_date == row["sensing_date"],
            HistoricalPedestrianCount.hour_of_day == row["hour_of_day"],
        )
    )
    if existing is not None:
        stats.counts_skipped += 1
        return

    db.add(
        HistoricalPedestrianCount(
            sensor_id=row["sensor_id"],
            sensing_date=row["sensing_date"],
            hour_of_day=row["hour_of_day"],
            direction_1_count=row["direction_1_count"],
            direction_2_count=row["direction_2_count"],
            total_count=row["total_count"],
            source_record_id=row["source_record_id"],
        )
    )
    stats.counts_inserted += 1


def import_rows(input_path: Path) -> ImportStats:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    stats = ImportStats()
    rows = load_rows(input_path)

    with SessionLocal() as db:
        for raw_row in rows:
            try:
                row = validate_row(raw_row)
                upsert_sensor(db, row, stats)
                insert_count_if_missing(db, row, stats)
            except Exception as exc:
                stats.invalid_rows += 1
                print(f"Skipping invalid row: {exc.__class__.__name__}: {exc}")

        db.commit()

    return stats


def main() -> None:
    args = parse_args()
    stats = import_rows(Path(args.input))
    print(f"sensors_inserted={stats.sensors_inserted}")
    print(f"sensors_updated={stats.sensors_updated}")
    print(f"counts_inserted={stats.counts_inserted}")
    print(f"counts_skipped={stats.counts_skipped}")
    print(f"invalid_rows={stats.invalid_rows}")


if __name__ == "__main__":
    main()
