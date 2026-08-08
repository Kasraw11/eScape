from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteSegmentCandidate:
    """
    Represents one section of a journey.

    A segment may represent walking, tram, train or bus
    when multimodal routing is added later.
    """

    # Position of this segment within the complete journey.
    segment_sequence: int

    # Encoded geometry used for drawing the route.
    encoded_polyline: str | None = None

    # Decoded latitude / longitude points.
    # These are also used for pedestrian sensor matching.
    points: list[tuple[float, float]] = field(
        default_factory=list
    )

    # Distance of this segment in metres.
    distance_m: int | None = None

    # Duration of this segment in seconds.
    duration_seconds: int | None = None

    # Transport used for this individual segment.
    # Later this can be:
    # walking, tram, train or bus.
    mode: str = "walking"


@dataclass(frozen=True)
class RouteCandidate:
    """
    Represents one complete journey returned
    by a routing provider.
    """

    # Provider-independent identifier for the route.
    route_identifier: str

    # Geometry for the complete journey.
    encoded_polyline: str | None

    # Decoded latitude / longitude points for the route.
    points: list[tuple[float, float]]

    # Total estimated journey duration.
    estimated_travel_minutes: int

    # Individual sections that make up the journey.
    segments: list[RouteSegmentCandidate] = field(
        default_factory=list
    )