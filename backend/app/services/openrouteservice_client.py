from typing import Any

import httpx

from app.core.config import get_settings
from app.core.crowd import CrowdLevel
from app.core.validation import Coordinate
from app.schemas.routes import RouteOption, RoutePlanRequest, RouteSegment
from app.services.routing_service import resolve_place, threshold_rank


class OpenRouteServiceClient:
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
                "/v2/directions/foot-walking/geojson",
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "coordinates": [
                        [origin.longitude, origin.latitude],
                        [destination.longitude, destination.latitude],
                    ],
                    "language": "en",
                    "units": "m",
                    "geometry": True,
                    "instructions": False,
                    "elevation": False,
                    "extra_info": ["surface", "waytype"],
                    "alternative_routes": {
                        "target_count": 2,
                        "weight_factor": 1.6,
                        "share_factor": 0.6,
                    },
                },
            )
            response.raise_for_status()

        return parse_openrouteservice_routes(response.json())


class OsmRouteServiceClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def compute_walking_routes(self, payload: RoutePlanRequest) -> list[RouteOption]:
        origin = resolve_place(payload.origin.label, payload.origin.coordinates)
        destination = resolve_place(payload.destination.label, payload.destination.coordinates)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = await client.get(
                "/route/v1/foot/{coords}".format(
                    coords=f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
                ),
                params={
                    "alternatives": "true",
                    "steps": "false",
                    "geometries": "geojson",
                    "overview": "full",
                },
            )
            response.raise_for_status()

        return parse_osrm_routes(response.json())


def get_openrouteservice_client() -> OpenRouteServiceClient:
    settings = get_settings()
    return OpenRouteServiceClient(
        api_key=settings.openrouteservice_api_key,
        base_url=settings.openrouteservice_base_url,
        timeout_seconds=settings.external_api_timeout_seconds,
    )


def get_osm_route_client() -> OsmRouteServiceClient:
    settings = get_settings()
    return OsmRouteServiceClient(
        base_url="https://router.project-osrm.org",
        timeout_seconds=settings.external_api_timeout_seconds,
    )


def parse_openrouteservice_routes(payload: dict[str, Any]) -> list[RouteOption]:
    features = payload.get("features")
    if not isinstance(features, list):
        return []

    route_options: list[RouteOption] = []
    for index, feature in enumerate(features[:4]):
        if not isinstance(feature, dict):
            continue

        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        properties = feature.get("properties", {})
        if not isinstance(properties, dict):
            continue

        summary = properties.get("summary", {})
        if not isinstance(summary, dict):
            continue

        distance_m = summary.get("distance")
        duration_s = summary.get("duration")
        if not isinstance(distance_m, (int, float)) or not isinstance(duration_s, (int, float)):
            continue

        positions = extract_positions(coordinates)
        if len(positions) < 2:
            continue

        title = "openrouteservice walking route" if index == 0 else f"openrouteservice alternative {index}"

        route_options.append(
            RouteOption(
                route_id=f"ors-{index + 1}",
                title=title,
                summary="Walking route geometry returned by openrouteservice.",
                distance_m=round(distance_m),
                estimated_duration_min=max(1, round(duration_s / 60)),
                sensory_level=CrowdLevel.MEDIUM,
                sensory_level_rank=threshold_rank(CrowdLevel.MEDIUM),
                high_congestion_segments=0,
                medium_congestion_segments=0,
                sensor_coverage="limited",
                matched_sensor_count=0,
                average_pedestrian_count=None,
                max_pedestrian_count=None,
                data_source="openrouteservice geometry; City of Melbourne live counts for sensory scoring",
                recommendation_reason="Route geometry comes from openrouteservice; sensory score is applied after sensor matching.",
                is_recommended=False,
                segments=positions_to_segments(positions),
            )
        )

    return route_options


def parse_osrm_routes(payload: dict[str, Any]) -> list[RouteOption]:
    routes = payload.get("routes")
    if not isinstance(routes, list):
        return []

    route_options: list[RouteOption] = []
    for index, route in enumerate(routes[:4]):
        if not isinstance(route, dict):
            continue

        geometry = route.get("geometry")
        if not isinstance(geometry, dict):
            continue

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        distance_m = route.get("distance")
        duration_s = route.get("duration")
        if not isinstance(distance_m, (int, float)) or not isinstance(duration_s, (int, float)):
            continue

        positions = extract_positions(coordinates)
        if len(positions) < 2:
            continue

        title = "OSRM walking route" if index == 0 else f"OSRM alternative {index}"
        route_options.append(
            RouteOption(
                route_id=f"osrm-{index + 1}",
                title=title,
                summary="Walking route geometry returned by OSRM.",
                distance_m=round(distance_m),
                estimated_duration_min=max(1, round(duration_s / 60)),
                sensory_level=CrowdLevel.MEDIUM,
                sensory_level_rank=threshold_rank(CrowdLevel.MEDIUM),
                high_congestion_segments=0,
                medium_congestion_segments=0,
                sensor_coverage="limited",
                matched_sensor_count=0,
                average_pedestrian_count=None,
                max_pedestrian_count=None,
                data_source="OSRM geometry; City of Melbourne live counts for sensory scoring",
                recommendation_reason="Route geometry comes from OSRM; sensory score is applied after sensor matching.",
                is_recommended=False,
                segments=positions_to_segments(positions),
            )
        )

    return route_options


def extract_positions(coordinates: list[Any]) -> list[Coordinate]:
    positions: list[Coordinate] = []
    for pair in coordinates:
        if (
            isinstance(pair, list)
            and len(pair) >= 2
            and isinstance(pair[0], (int, float))
            and isinstance(pair[1], (int, float))
        ):
            positions.append(Coordinate(latitude=pair[1], longitude=pair[0]))
    return positions


def positions_to_segments(positions: list[Coordinate]) -> list[RouteSegment]:
    return [
        RouteSegment(start=start, end=end, sensory_level=CrowdLevel.MEDIUM)
        for start, end in zip(positions, positions[1:])
    ]
