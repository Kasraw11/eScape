from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher
from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.data.refuge_hours_overrides import REFUGE_HOURS_OVERRIDES
from app.models.point_of_interest import PointOfInterest


LANDMARKS_SOURCE = "City of Melbourne Open Data: Landmarks and places of interest"
ASSETS_SOURCE = "City of Melbourne Open Data: Assets for environmental reporting"
logger = logging.getLogger(__name__)

OVERPASS_OPENING_HOURS_QUERY = """
[out:json][timeout:25];
(
  nwr["leisure"="park"]["opening_hours"](-37.86,144.90,-37.77,145.05);
  nwr["amenity"="library"]["opening_hours"](-37.86,144.90,-37.77,145.05);
);
out center tags;
""".strip()


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
            if settings.osm_opening_hours_enrichment_enabled:
                combined = await self._enrich_opening_hours(http_client, combined)
            combined = [_apply_manual_hours_override(record) for record in combined]
        except MelbourneRefugeDataError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise MelbourneRefugeDataError("Melbourne refuge data request failed") from exc
        finally:
            if owns_client:
                await http_client.aclose()
        return combined

    async def _enrich_opening_hours(
        self,
        client: httpx.AsyncClient,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        try:
            response = await client.get(
                settings.osm_overpass_api_url,
                params={"data": OVERPASS_OPENING_HOURS_QUERY},
                headers={"User-Agent": "eScape sensory navigation student project"},
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("OSM opening-hours enrichment was unavailable: %s", exc)
            return records

        candidates = [_osm_hours_candidate(element) for element in elements if isinstance(element, dict)]
        candidates = [candidate for candidate in candidates if candidate is not None]
        return [_apply_osm_hours(record, candidates) for record in records]


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
            parsed = _parse_osm_opening_hours(value)
        return json.dumps(parsed, sort_keys=True) if isinstance(parsed, dict) else None
    return None


@dataclass(frozen=True)
class OsmHoursCandidate:
    name: str
    latitude: float
    longitude: float
    opening_hours: str


def _osm_hours_candidate(element: dict[str, Any]) -> OsmHoursCandidate | None:
    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None
    name = str(tags.get("name") or "").strip()
    opening_hours = str(tags.get("opening_hours") or "").strip()
    center = element.get("center") if isinstance(element.get("center"), dict) else element
    try:
        latitude = float(center["lat"])
        longitude = float(center["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not name or not opening_hours or _parse_osm_opening_hours(opening_hours) is None:
        return None
    return OsmHoursCandidate(name, latitude, longitude, opening_hours)


def _apply_osm_hours(record: dict[str, Any], candidates: list[OsmHoursCandidate]) -> dict[str, Any]:
    if record.get("opening_hours"):
        return record
    location = _record_location(record)
    name = str(record.get("feature_name") or record.get("asset_name") or "").strip()
    if location is None or not name:
        return record

    normalized_name = _normalized_name(name)
    matches = []
    for candidate in candidates:
        distance = _distance_m(location, (candidate.latitude, candidate.longitude))
        similarity = SequenceMatcher(None, normalized_name, _normalized_name(candidate.name)).ratio()
        if distance <= 250 and similarity >= 0.82:
            matches.append((similarity, -distance, candidate))
    if not matches:
        return record
    matched = max(matches, key=lambda item: (item[0], item[1]))[2]
    return {**record, "opening_hours": matched.opening_hours}


def _apply_manual_hours_override(record: dict[str, Any]) -> dict[str, Any]:
    name = str(record.get("feature_name") or record.get("asset_name") or "").strip()
    override = REFUGE_HOURS_OVERRIDES.get(_normalized_name(name))
    if override is None:
        return record
    return {**record, "opening_hours": override["opening_hours"]}


def _record_location(record: dict[str, Any]) -> tuple[float, float] | None:
    coordinates = record.get("co_ordinates")
    try:
        if isinstance(coordinates, dict):
            return float(coordinates["lat"]), float(coordinates["lon"])
        return float(record["latitude"]), float(record["longitude"])
    except (KeyError, TypeError, ValueError):
        return None


def _normalized_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _distance_m(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*origin, *destination))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))


DAY_INDEX = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _parse_osm_opening_hours(value: str) -> dict[str, list[list[str]]] | None:
    value = value.strip()
    if value == "24/7":
        return {day: [["00:00", "23:59"]] for day in DAY_NAMES}

    schedule: dict[str, list[list[str]]] = {}
    for rule in value.split(";"):
        match = re.fullmatch(
            r"\s*((?:Mo|Tu|We|Th|Fr|Sa|Su)(?:-(?:Mo|Tu|We|Th|Fr|Sa|Su))?(?:,(?:Mo|Tu|We|Th|Fr|Sa|Su))*)\s+(off|(?:\d{1,2}:\d{2}-\d{1,2}:\d{2})(?:,(?:\d{1,2}:\d{2}-\d{1,2}:\d{2}))*)\s*",
            rule,
        )
        if not match:
            return None
        days = _expand_days(match.group(1))
        periods = [] if match.group(2) == "off" else [period.split("-", 1) for period in match.group(2).split(",")]
        if any(not _valid_time_period(period) for period in periods):
            return None
        for day in days:
            schedule[DAY_NAMES[day]] = periods
    return schedule or None


def _expand_days(value: str) -> list[int]:
    days: list[int] = []
    for part in value.split(","):
        if "-" not in part:
            days.append(DAY_INDEX[part])
            continue
        start, end = (DAY_INDEX[item] for item in part.split("-", 1))
        days.extend(range(start, end + 1) if start <= end else [*range(start, 7), *range(0, end + 1)])
    return list(dict.fromkeys(days))


def _valid_time_period(period: list[str]) -> bool:
    if len(period) != 2:
        return False
    for value in period:
        try:
            hour, minute = (int(part) for part in value.split(":"))
        except (ValueError, TypeError):
            return False
        if not 0 <= hour <= 24 or not 0 <= minute <= 59 or (hour == 24 and minute != 0):
            return False
    return True
