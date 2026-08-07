from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.schemas.route_planning import RoutePlanningRequest


class GoogleMapsServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteSegmentCandidate:
    segment_sequence: int
    encoded_polyline: str | None
    points: list[tuple[float, float]]
    distance_m: int | None
    duration_seconds: int | None


@dataclass(frozen=True)
class RouteCandidate:
    route_identifier: str
    encoded_polyline: str | None
    points: list[tuple[float, float]]
    estimated_travel_minutes: int
    segments: list[RouteSegmentCandidate]


def decode_polyline(polyline: str | None) -> list[tuple[float, float]]:
    if not polyline:
        return []

    coordinates: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0

    while index < len(polyline):
        result = 1
        shift = 0
        while True:
            byte = ord(polyline[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lat += ~(result >> 1) if result & 1 else result >> 1

        result = 1
        shift = 0
        while True:
            byte = ord(polyline[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lng += ~(result >> 1) if result & 1 else result >> 1

        coordinates.append((lat * 1e-5, lng * 1e-5))

    return coordinates


class GoogleMapsService:
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key if api_key is not None else settings.google_maps_api_key
        self.timeout_seconds = timeout_seconds

    async def get_route_alternatives(self, request: RoutePlanningRequest) -> list[RouteCandidate]:
        if not self.api_key:
            raise GoogleMapsServiceError("Google Maps API key is not configured")

        params = {
            "origin": f"{request.origin_latitude},{request.origin_longitude}",
            "destination": f"{request.destination_latitude},{request.destination_longitude}",
            "mode": request.travel_mode,
            "alternatives": "true",
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.directions_url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleMapsServiceError("Google Maps request failed") from exc

        payload = response.json()
        status = payload.get("status")
        if status != "OK":
            raise GoogleMapsServiceError(f"Google Maps returned status {status or 'UNKNOWN'}")

        return self._convert_routes(payload.get("routes", []))

    def _convert_routes(self, routes: list[dict[str, Any]]) -> list[RouteCandidate]:
        converted: list[RouteCandidate] = []
        for route_index, route in enumerate(routes, start=1):
            overview_polyline = route.get("overview_polyline", {}).get("points")
            legs = route.get("legs") or []
            steps = legs[0].get("steps", []) if legs else []
            duration_seconds = sum((step.get("duration") or {}).get("value", 0) for step in steps)
            segments = [
                RouteSegmentCandidate(
                    segment_sequence=step_index,
                    encoded_polyline=(step.get("polyline") or {}).get("points"),
                    points=decode_polyline((step.get("polyline") or {}).get("points")),
                    distance_m=(step.get("distance") or {}).get("value"),
                    duration_seconds=(step.get("duration") or {}).get("value"),
                )
                for step_index, step in enumerate(steps, start=1)
            ]
            converted.append(
                RouteCandidate(
                    route_identifier=route.get("summary") or f"google_route_{route_index}",
                    encoded_polyline=overview_polyline,
                    points=decode_polyline(overview_polyline),
                    estimated_travel_minutes=max(1, round(duration_seconds / 60)),
                    segments=segments,
                )
            )
        return converted
