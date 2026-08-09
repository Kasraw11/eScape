from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.point_of_interest import PointOfInterest


LANDMARKS_SOURCE = "City of Melbourne Open Data: Landmarks and places of interest"
ASSETS_SOURCE = "City of Melbourne Open Data: Assets for environmental reporting"


class MelbourneRefugeDataError(RuntimeError):
    pass


@dataclass
class RefugeImportStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    invalid: int = 0


@dataclass(frozen=True)
class ValidatedRefuge:
    source: str
    source_record_id: str
    category: str
    sub_theme: str | None
    name: str
    address: str | None
    latitude: float
    longitude: float
    opening_hours: str | None
    accessibility_notes: str | None
    sensory_notes: str
    last_updated_at: datetime


class MelbourneRefugeClient:
    async def fetch(self, client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=settings.melbourne_refuge_api_timeout_seconds)
        sources = (
            ("landmarks", settings.melbourne_landmarks_api_url),
            ("assets", settings.melbourne_environmental_assets_api_url),
        )
        combined: list[dict[str, Any]] = []
        try:
            for dataset_kind, url in sources:
                offset = 0
                while True:
                    response = await http_client.get(
                        url,
                        params={"limit": settings.melbourne_refuge_api_limit, "offset": offset},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    results = payload.get("results") if isinstance(payload, dict) else None
                    if not isinstance(results, list):
                        raise MelbourneRefugeDataError("Melbourne refuge data response was invalid")
                    combined.extend({"_dataset_kind": dataset_kind, **record} for record in results if isinstance(record, dict))
                    offset += len(results)
                    total_count = payload.get("total_count", offset)
                    if not results or offset >= total_count:
                        break
        except MelbourneRefugeDataError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise MelbourneRefugeDataError("Melbourne refuge data request failed") from exc
        finally:
            if owns_client:
                await http_client.aclose()
        return combined


class RefugeIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(self, raw_records: list[dict[str, Any]], imported_at: datetime | None = None) -> RefugeImportStats:
        stats = RefugeImportStats()
        seen: set[tuple[str, str]] = set()
        timestamp = imported_at or datetime.now(timezone.utc)

        for record in raw_records:
            try:
                refuge = validate_refuge(record, timestamp)
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue
            if refuge is None:
                stats.skipped += 1
                continue
            key = (refuge.source, refuge.source_record_id)
            if key in seen:
                stats.skipped += 1
                continue
            seen.add(key)

            existing = self.db.scalar(
                select(PointOfInterest).where(
                    PointOfInterest.source == refuge.source,
                    PointOfInterest.source_record_id == refuge.source_record_id,
                )
            )
            values = {
                "theme": refuge.category,
                "sub_theme": refuge.sub_theme,
                "feature_name": refuge.name,
                "address": refuge.address,
                "latitude": Decimal(str(refuge.latitude)),
                "longitude": Decimal(str(refuge.longitude)),
                "coordinates_text": f"{refuge.latitude},{refuge.longitude}",
                "opening_hours": refuge.opening_hours,
                "is_sensory_refuge": True,
                "source": refuge.source,
                "source_record_id": refuge.source_record_id,
                "accessibility_notes": refuge.accessibility_notes,
                "sensory_notes": refuge.sensory_notes,
                "last_updated_at": refuge.last_updated_at,
            }
            if existing is None:
                self.db.add(PointOfInterest(**values))
                stats.inserted += 1
                continue
            changed = any(getattr(existing, field) != value for field, value in values.items())
            if changed:
                for field, value in values.items():
                    setattr(existing, field, value)
                stats.updated += 1
            else:
                stats.skipped += 1
        return stats


def validate_refuge(record: dict[str, Any], imported_at: datetime) -> ValidatedRefuge | None:
    dataset_kind = record.get("_dataset_kind")
    if dataset_kind == "landmarks":
        sub_theme = str(record.get("sub_theme") or "").strip()
        name = str(record.get("feature_name") or "").strip()
        coordinates = record.get("co_ordinates")
        if isinstance(coordinates, dict):
            latitude = float(coordinates["lat"])
            longitude = float(coordinates["lon"])
        elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            latitude, longitude = float(coordinates[0]), float(coordinates[1])
        else:
            raise ValueError("Missing coordinates")
        if "park/garden/reserve" in sub_theme.casefold():
            category = "Park"
        elif "library" in name.casefold() or "library" in sub_theme.casefold():
            category = "Library"
        else:
            return None
        source = LANDMARKS_SOURCE
        address = None
        accessibility_notes = None
    elif dataset_kind == "assets":
        asset_type = str(record.get("asset_type") or "").strip()
        name = str(record.get("asset_name") or "").strip()
        if asset_type.casefold() != "library facilities":
            return None
        category = "Library"
        sub_theme = asset_type
        latitude, longitude = float(record["latitude"]), float(record["longitude"])
        address_parts = [record.get("address"), record.get("suburb"), record.get("postcode")]
        address = ", ".join(str(part).strip() for part in address_parts if part not in (None, "")) or None
        accessibility_notes = None
        source = ASSETS_SOURCE
    else:
        raise ValueError("Unknown dataset")

    if not name or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid refuge")
    opening_hours = _structured_hours(record.get("opening_hours"))
    source_record_id = str(record.get("id") or record.get("asset_id") or "").strip()
    if not source_record_id:
        stable = f"{source}|{category}|{name.casefold()}|{latitude:.6f}|{longitude:.6f}"
        source_record_id = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:32]
    return ValidatedRefuge(
        source=source,
        source_record_id=source_record_id,
        category=category,
        sub_theme=sub_theme or None,
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        opening_hours=opening_hours,
        accessibility_notes=accessibility_notes,
        sensory_notes="Potential quiet space identified from a defensible public-space category; quietness is not guaranteed.",
        last_updated_at=imported_at,
    )


def _structured_hours(value: Any) -> str | None:
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return json.dumps(parsed, sort_keys=True) if isinstance(parsed, dict) else None
    return None
