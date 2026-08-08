from __future__ import annotations
from app.config import settings

from typing import Any

import httpx

from app.schemas.route_planning import RoutePlanningRequest
from app.services.routing_models import (
    RouteCandidate,
    RouteSegmentCandidate,
)
from app.services.routing_service import RoutingServiceError


class OSRMServiceError(RoutingServiceError):
    """
    Raised when OSRM cannot generate route information.
    """

    pass


class OSRMService:
    """
    OSM-based routing provider using OSRM.

    For the current MVP, this service generates walking routes.

    Later, OpenTripPlanner can replace this service when we
    add GTFS-based tram, train and bus routing.
    """

    def __init__(
        self,
        base_url: str | None = None,
        profile: str = "foot",
        timeout_seconds: float = 10.0,
    ) -> None:
        """
        Creates the OSRM routing service.

        If no base_url is provided directly, use the
        OSRM_BASE_URL value loaded from backend/.env.
        """

        self.base_url = (
            base_url or settings.osrm_base_url
        ).rstrip("/")

        self.profile = profile
        self.timeout_seconds = timeout_seconds

    async def get_route_alternatives(
        self,
        request: RoutePlanningRequest,
    ) -> list[RouteCandidate]:
        """
        Requests walking route alternatives from OSRM.

        The result is converted into the generic RouteCandidate
        format used by the rest of the eScape backend.
        """

        # IMPORTANT:
        # OSRM coordinates use longitude,latitude order.
        coordinates = (
            f"{request.origin_longitude},"
            f"{request.origin_latitude};"
            f"{request.destination_longitude},"
            f"{request.destination_latitude}"
        )

        url = (
            f"{self.base_url}/route/v1/"
            f"{self.profile}/{coordinates}"
        )

        params = {
            # Ask OSRM for alternative routes when available.
            "alternatives": "true",

            # Return individual route steps.
            "steps": "true",

            # GeoJSON is easier for us to work with than
            # provider-specific encoded polyline formats.
            "geometries": "geojson",

            # Keep the full route geometry for sensor matching.
            "overview": "full",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.get(
                    url,
                    params=params,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise OSRMServiceError(
                "OSRM route request failed"
            ) from exc

        try:
            payload = response.json()

        except ValueError as exc:
            raise OSRMServiceError(
                "OSRM returned an invalid response"
            ) from exc

        # OSRM returns "Ok" when the request succeeds.
        if payload.get("code") != "Ok":
            message = (
                payload.get("message")
                or "OSRM could not generate a route"
            )

            raise OSRMServiceError(message)

        return self._convert_routes(
            payload.get("routes", [])
        )

    def _convert_routes(
        self,
        routes: list[dict[str, Any]],
    ) -> list[RouteCandidate]:
        """
        Converts OSRM routes into provider-independent
        RouteCandidate objects.

        This allows routes.py and the sensory-scoring system
        to work without knowing which provider generated
        the routes.
        """

        converted: list[RouteCandidate] = []

        for route_index, route in enumerate(
            routes,
            start=1,
        ):
            route_points = self._geometry_points(
                route.get("geometry")
            )

            segments: list[RouteSegmentCandidate] = []

            segment_sequence = 1

            # A route may contain one or more legs.
            for leg in route.get("legs") or []:
                steps = leg.get("steps") or []

                for step in steps:
                    segment = self._convert_step(
                        step=step,
                        segment_sequence=segment_sequence,
                    )

                    segments.append(segment)

                    segment_sequence += 1

            # If OSRM did not return step information,
            # use the complete route as a single segment.
            if not segments:
                segments.append(
                    RouteSegmentCandidate(
                        segment_sequence=1,
                        encoded_polyline=None,
                        points=route_points,
                        distance_m=self._to_int(
                            route.get("distance")
                        ),
                        duration_seconds=self._to_int(
                            route.get("duration")
                        ),
                        mode="walking",
                    )
                )

            duration_seconds = float(
                route.get("duration") or 0
            )

            converted.append(
                RouteCandidate(
                    route_identifier=(
                        f"osrm_route_{route_index}"
                    ),

                    # We are using GeoJSON geometry,
                    # so no encoded polyline is required.
                    encoded_polyline=None,

                    points=route_points,

                    estimated_travel_minutes=max(
                        1,
                        round(duration_seconds / 60),
                    ),

                    segments=segments,
                )
            )

        return converted

    def _convert_step(
        self,
        step: dict[str, Any],
        segment_sequence: int,
    ) -> RouteSegmentCandidate:
        """
        Converts one OSRM route step into an eScape
        RouteSegmentCandidate.

        For the current MVP every OSRM segment is walking.
        """

        return RouteSegmentCandidate(
            segment_sequence=segment_sequence,

            encoded_polyline=None,

            points=self._geometry_points(
                step.get("geometry")
            ),

            distance_m=self._to_int(
                step.get("distance")
            ),

            duration_seconds=self._to_int(
                step.get("duration")
            ),

            mode="walking",
        )

    @staticmethod
    def _geometry_points(
        geometry: dict[str, Any] | None,
    ) -> list[tuple[float, float]]:
        """
        Converts OSRM GeoJSON coordinates into the
        (latitude, longitude) format used by eScape.

        GeoJSON gives:
            [longitude, latitude]

        eScape uses:
            (latitude, longitude)
        """

        if not geometry:
            return []

        coordinates = geometry.get("coordinates")

        if not isinstance(coordinates, list):
            return []

        points: list[tuple[float, float]] = []

        for coordinate in coordinates:
            if (
                not isinstance(coordinate, list)
                or len(coordinate) < 2
            ):
                continue

            longitude = coordinate[0]
            latitude = coordinate[1]

            try:
                points.append(
                    (
                        float(latitude),
                        float(longitude),
                    )
                )

            except (TypeError, ValueError):
                continue

        return points

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        """
        Converts OSRM numeric distance/duration values
        into integers used by our route models.
        """

        if value is None:
            return None

        try:
            return round(float(value))

        except (TypeError, ValueError):
            return None