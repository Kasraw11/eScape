from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.schemas.route_planning import RoutePlanningRequest

# Generic route models shared by all routing providers.
from app.services.routing_models import (
    RouteCandidate,
    RouteSegmentCandidate,
)

# Generic routing error used by routes.py.
from app.services.routing_service import RoutingServiceError


class GoogleMapsServiceError(RoutingServiceError):
    """
    Raised when Google Maps cannot return route information.

    This extends the generic RoutingServiceError so routes.py
    does not need to depend directly on Google-specific errors.
    """

    pass


def decode_polyline(
    polyline: str | None,
) -> list[tuple[float, float]]:
    """
    Converts a Google encoded polyline into
    latitude / longitude coordinate pairs.

    The decoded coordinates are later used for:
    - displaying routes
    - matching pedestrian sensors
    - sensory scoring
    """

    if not polyline:
        return []

    coordinates: list[tuple[float, float]] = []

    index = 0
    lat = 0
    lng = 0

    while index < len(polyline):
        result = 1
        shift = 0

        # Decode latitude.
        while True:
            byte = ord(polyline[index]) - 63 - 1
            index += 1

            result += byte << shift
            shift += 5

            if byte < 0x1F:
                break

        lat += (
            ~(result >> 1)
            if result & 1
            else result >> 1
        )

        result = 1
        shift = 0

        # Decode longitude.
        while True:
            byte = ord(polyline[index]) - 63 - 1
            index += 1

            result += byte << shift
            shift += 5

            if byte < 0x1F:
                break

        lng += (
            ~(result >> 1)
            if result & 1
            else result >> 1
        )

        coordinates.append(
            (
                lat * 1e-5,
                lng * 1e-5,
            )
        )

    return coordinates


class GoogleMapsService:
    """
    Temporary routing provider.

    Google Maps is still used while the project is being
    migrated toward OSM / OpenTripPlanner.

    This class follows the generic RoutingService interface,
    so it can later be replaced without changing routes.py.
    """

    directions_url = (
        "https://maps.googleapis.com/maps/api/directions/json"
    )

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        """
        Creates the Google routing service.

        If no API key is provided directly, the key is
        loaded from the application settings.
        """

        self.api_key = (
            api_key
            if api_key is not None
            else settings.google_maps_api_key
        )

        self.timeout_seconds = timeout_seconds

    async def get_route_alternatives(
        self,
        request: RoutePlanningRequest,
    ) -> list[RouteCandidate]:
        """
        Requests alternative routes from Google Maps.

        The returned Google routes are converted into the
        generic RouteCandidate format used by eScape.

        This method can later be replaced by an
        OpenTripPlanner implementation.
        """

        if not self.api_key:
            raise GoogleMapsServiceError(
                "Google Maps API key is not configured"
            )

        params = {
            "origin": (
                f"{request.origin_latitude},"
                f"{request.origin_longitude}"
            ),
            "destination": (
                f"{request.destination_latitude},"
                f"{request.destination_longitude}"
            ),

            # Temporary while Google is still the provider.
            # Later OpenTripPlanner will determine the
            # walking / transit journey legs automatically.
            "mode": request.travel_mode,

            "alternatives": "true",
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:

                response = await client.get(
                    self.directions_url,
                    params=params,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise GoogleMapsServiceError(
                "Google Maps request failed"
            ) from exc

        payload = response.json()

        status = payload.get("status")

        if status != "OK":
            raise GoogleMapsServiceError(
                f"Google Maps returned status "
                f"{status or 'UNKNOWN'}"
            )

        return self._convert_routes(
            payload.get("routes", [])
        )

    def _convert_routes(
        self,
        routes: list[dict[str, Any]],
    ) -> list[RouteCandidate]:
        """
        Converts Google Maps route responses into
        provider-independent RouteCandidate objects.

        routes.py and the sensory-scoring system should
        only work with these generic objects.
        """

        converted: list[RouteCandidate] = []

        for route_index, route in enumerate(
            routes,
            start=1,
        ):
            overview_polyline = (
                route.get(
                    "overview_polyline",
                    {},
                ).get("points")
            )

            legs = route.get("legs") or []

            # Google usually returns one leg for the
            # current origin → destination request.
            steps = (
                legs[0].get("steps", [])
                if legs
                else []
            )

            duration_seconds = sum(
                (step.get("duration") or {}).get(
                    "value",
                    0,
                )
                for step in steps
            )

            # Convert each Google step into a generic
            # eScape route segment.
            segments = [
                RouteSegmentCandidate(
                    segment_sequence=step_index,

                    encoded_polyline=(
                        step.get("polyline")
                        or {}
                    ).get("points"),

                    points=decode_polyline(
                        (
                            step.get("polyline")
                            or {}
                        ).get("points")
                    ),

                    distance_m=(
                        step.get("distance")
                        or {}
                    ).get("value"),

                    duration_seconds=(
                        step.get("duration")
                        or {}
                    ).get("value"),

                    # Temporary.
                    # Once OpenTripPlanner is used,
                    # segments can contain walking,
                    # tram, train and bus modes.
                    mode=request_mode_from_step(step),
                )
                for step_index, step in enumerate(
                    steps,
                    start=1,
                )
            ]

            converted.append(
                RouteCandidate(
                    route_identifier=(
                        route.get("summary")
                        or f"google_route_{route_index}"
                    ),

                    encoded_polyline=overview_polyline,

                    points=decode_polyline(
                        overview_polyline
                    ),

                    estimated_travel_minutes=max(
                        1,
                        round(
                            duration_seconds / 60
                        ),
                    ),

                    segments=segments,
                )
            )

        return converted


def request_mode_from_step(
    step: dict[str, Any],
) -> str:
    """
    Converts Google's step travel mode into the
    generic segment mode used by eScape.

    Google currently returns modes such as WALKING
    or TRANSIT.

    More detailed tram / train / bus information will
    come later from OpenTripPlanner / GTFS.
    """

    travel_mode = str(
        step.get("travel_mode", "WALKING")
    ).lower()

    if travel_mode == "transit":
        return "transit"

    return "walking"