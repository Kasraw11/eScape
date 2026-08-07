from typing import Any

import httpx

from app.core.crowd import CrowdLevel
from app.core.config import get_settings
from app.core.validation import Coordinate
from app.schemas.routes import RouteOption, RoutePlanRequest, RouteSegment
from app.services.routing_service import resolve_place, threshold_rank


class GoogleRoutesClient:
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    async def compute_walking_routes(self, payload: RoutePlanRequest) -> list[RouteOption]:
        if not self.is_configured:
            return []

        origin = resolve_place(payload.origin.label, payload.origin.coordinates)
        destination = resolve_place(payload.destination.label, payload.destination.coordinates)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = await client.post(
                "/directions/v2:computeRoutes",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": (
                        "routes.duration,routes.distanceMeters,"
                        "routes.routeLabels,routes.polyline.geoJsonLinestring"
                    ),
                },
                json={
                    "origin": {"location": {"latLng": to_google_lat_lng(origin)}},
                    "destination": {"location": {"latLng": to_google_lat_lng(destination)}},
                    "travelMode": "WALK",
                    "computeAlternativeRoutes": True,
                    "polylineEncoding": "GEO_JSON_LINESTRING",
                    "polylineQuality": "HIGH_QUALITY",
                    "languageCode": "en-AU",
                    "units": "METRIC",
                },
            )
            response.raise_for_status()

        return parse_google_routes(response.json())


def get_google_routes_client() -> GoogleRoutesClient:
    settings = get_settings()
    return GoogleRoutesClient(
        api_key=settings.google_maps_api_key,
        base_url=settings.google_routes_base_url,
        timeout_seconds=settings.external_api_timeout_seconds,
    )


def to_google_lat_lng(coordinate: Coordinate) -> dict[str, float]:
    return {
        "latitude": coordinate.latitude,
        "longitude": coordinate.longitude,
    }


def parse_google_routes(payload: dict[str, Any]) -> list[RouteOption]:
    raw_routes = payload.get("routes")
    if not isinstance(raw_routes, list):
        return []

    route_options: list[RouteOption] = []
    for index, raw_route in enumerate(raw_routes[:4]):
        if not isinstance(raw_route, dict):
            continue

        positions = extract_geojson_positions(raw_route)
        if len(positions) < 2:
            continue

        distance_m = raw_route.get("distanceMeters")
        if not isinstance(distance_m, int):
            continue

        duration_min = parse_duration_minutes(raw_route.get("duration"))
        is_default = "DEFAULT_ROUTE" in raw_route.get("routeLabels", [])
        title = "Google walking route" if is_default or index == 0 else f"Google alternative {index}"

        route_options.append(
            RouteOption(
                route_id=f"google-{index + 1}",
                title=title,
                summary="Walking route geometry returned by Google Routes API.",
                distance_m=distance_m,
                estimated_duration_min=duration_min,
                sensory_level=CrowdLevel.MEDIUM,
                sensory_level_rank=threshold_rank(CrowdLevel.MEDIUM),
                high_congestion_segments=0,
                medium_congestion_segments=0,
                sensor_coverage="limited",
                matched_sensor_count=0,
                average_pedestrian_count=None,
                max_pedestrian_count=None,
                data_source="Google Routes API geometry; City of Melbourne live counts for sensory scoring",
                recommendation_reason="Route geometry comes from Google; sensory score is applied after sensor matching.",
                is_recommended=False,
                segments=positions_to_segments(positions),
            )
        )

    return route_options


def extract_geojson_positions(raw_route: dict[str, Any]) -> list[Coordinate]:
    coordinates = (
        raw_route.get("polyline", {})
        .get("geoJsonLinestring", {})
        .get("coordinates")
    )
    if not isinstance(coordinates, list):
        return []

    positions: list[Coordinate] = []
    for pair in coordinates:
        if (
            isinstance(pair, list)
            and len(pair) >= 2
            and isinstance(pair[0], int | float)
            and isinstance(pair[1], int | float)
        ):
            positions.append(Coordinate(latitude=pair[1], longitude=pair[0]))

    return positions


def positions_to_segments(positions: list[Coordinate]) -> list[RouteSegment]:
    return [
        RouteSegment(start=start, end=end, sensory_level=CrowdLevel.MEDIUM)
        for start, end in zip(positions, positions[1:])
    ]


def parse_duration_minutes(duration: Any) -> int:
    if not isinstance(duration, str) or not duration.endswith("s"):
        return 0

    try:
        seconds = int(duration.removesuffix("s"))
    except ValueError:
        return 0

    return max(1, round(seconds / 60))
