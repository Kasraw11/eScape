from __future__ import annotations

from typing import Protocol

from app.schemas.route_planning import RoutePlanningRequest
from app.services.routing_models import RouteCandidate


class RoutingServiceError(Exception):
    """
    Raised when a routing provider cannot generate routes.
    """

    pass


class RoutingService(Protocol):
    """
    Common interface for any routing provider.

    The API layer should depend on this interface instead of
    depending directly on Google Maps or OpenTripPlanner.
    """

    async def get_route_alternatives(
        self,
        request: RoutePlanningRequest,
    ) -> list[RouteCandidate]:
        """
        Returns alternative journeys between the requested
        origin and destination.
        """

        ...