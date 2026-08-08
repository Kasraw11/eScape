from math import asin, cos, radians, sin, sqrt

from app.core.crowd import CrowdLevel, classify_crowd_count
from app.core.validation import Coordinate
from app.schemas.crowd import PedestrianCount, SensorLocation
from app.schemas.routes import RouteOption, RoutePlanRequest, RoutePlanResponse, RouteSegment


KNOWN_PLACES = {
    "flinders street station": Coordinate(latitude=-37.8183, longitude=144.9671),
    "state library victoria": Coordinate(latitude=-37.8098, longitude=144.9652),
    "melbourne central": Coordinate(latitude=-37.8109, longitude=144.9629),
    "southern cross station": Coordinate(latitude=-37.8183, longitude=144.9525),
    "queen victoria market": Coordinate(latitude=-37.8076, longitude=144.9568),
    "fed square": Coordinate(latitude=-37.8179, longitude=144.9691),
    "federation square": Coordinate(latitude=-37.8179, longitude=144.9691),
    "rmit university": Coordinate(latitude=-37.8083, longitude=144.9638),
    "melbourne town hall": Coordinate(latitude=-37.8150, longitude=144.9666),
    "city library": Coordinate(latitude=-37.8170, longitude=144.9658),
}


def plan_routes(
    payload: RoutePlanRequest,
    sensor_locations: list[SensorLocation] | None = None,
    live_counts: list[PedestrianCount] | None = None,
    route_options: list[RouteOption] | None = None,
    count_source_label: str = "City of Melbourne live past-hour pedestrian counts",
    route_geometry_source: str = "demo",
) -> RoutePlanResponse:
    origin = resolve_place(payload.origin.label, payload.origin.coordinates)
    destination = resolve_place(payload.destination.label, payload.destination.coordinates)

    route_options = route_options or [
        build_route_option(
            route_id="balanced",
            title="Balanced CBD walk",
            summary="Most direct validated route shape available in the current MVP.",
            origin=origin,
            destination=destination,
            distance_multiplier=1.0,
            crowd_level=CrowdLevel.MEDIUM,
            high_segments=0,
            medium_segments=2,
            coverage="limited",
        ),
        build_route_option(
            route_id="calmer",
            title="Calmer streets alternative",
            summary="Adds a small detour to avoid the busiest mapped sensor corridor.",
            origin=origin,
            destination=destination,
            distance_multiplier=1.18,
            crowd_level=CrowdLevel.LOW,
            high_segments=0,
            medium_segments=1,
            coverage="limited",
        ),
        build_route_option(
            route_id="direct",
            title="Shortest available option",
            summary="Prioritises distance and may pass closer to busier pedestrian counters.",
            origin=origin,
            destination=destination,
            distance_multiplier=0.94,
            crowd_level=CrowdLevel.HIGH,
            high_segments=1,
            medium_segments=1,
            coverage="limited",
        ),
    ]

    if sensor_locations and live_counts:
        route_options = apply_live_crowd_scoring(
            route_options,
            sensor_locations,
            live_counts,
            count_source_label=count_source_label,
        )

    ranked_routes = sorted(
        route_options,
        key=lambda route: (
            route.sensory_level_rank,
            route.distance_m,
        ),
    )
    acceptable = [
        route
        for route in ranked_routes
        if route.sensory_level_rank <= threshold_rank(payload.crowd_threshold)
    ]
    recommended = acceptable[0] if acceptable else ranked_routes[0]

    final_routes = [
        route.model_copy(update={"is_recommended": route.route_id == recommended.route_id})
        for route in route_options
    ]

    if acceptable:
        message = "Recommended route fits the selected crowd comfort threshold."
    else:
        message = "No route satisfies the selected threshold yet, so the least crowded option is recommended."

    return RoutePlanResponse(
        status="planned",
        message=message,
        requested_threshold=payload.crowd_threshold,
        route_geometry_source=route_geometry_source,
        origin=origin,
        destination=destination,
        data_confidence="limited",
        limitations=[
            "Route geometry is deterministic MVP demo data until openrouteservice is connected.",
            "Crowd scoring uses nearby sensor readings and does not cover streets without sensors.",
            "Sensor coverage gaps must not be interpreted as low congestion.",
        ],
        routes=final_routes,
    )


def resolve_place(label: str, provided_coordinates: Coordinate | None) -> Coordinate:
    if provided_coordinates is not None:
        return provided_coordinates

    return KNOWN_PLACES.get(
        label.strip().lower(),
        Coordinate(latitude=-37.8136, longitude=144.9631),
    )


def build_route_option(
    route_id: str,
    title: str,
    summary: str,
    origin: Coordinate,
    destination: Coordinate,
    distance_multiplier: float,
    crowd_level: CrowdLevel,
    high_segments: int,
    medium_segments: int,
    coverage: str,
) -> RouteOption:
    base_distance = max(250, haversine_m(origin, destination))
    distance_m = round(base_distance * distance_multiplier)
    duration_min = max(4, round(distance_m / 80))
    waypoints = build_waypoints(route_id, origin, destination)

    reason = build_reason(crowd_level, high_segments, medium_segments)

    return RouteOption(
        route_id=route_id,
        title=title,
        summary=summary,
        distance_m=distance_m,
        estimated_duration_min=duration_min,
        sensory_level=crowd_level,
        sensory_level_rank=threshold_rank(crowd_level),
        high_congestion_segments=high_segments,
        medium_congestion_segments=medium_segments,
        sensor_coverage=coverage,
        data_source="MVP demo assumptions",
        recommendation_reason=reason,
        is_recommended=False,
        segments=waypoints_to_segments(waypoints, crowd_level),
    )


def build_waypoints(route_id: str, origin: Coordinate, destination: Coordinate) -> list[Coordinate]:
    if route_id == "calmer":
        north_lat = origin.latitude + 0.0022
        west_lng = origin.longitude - 0.0010
        east_lng = destination.longitude + 0.0006
        south_lat = destination.latitude + 0.0004
        return [
            origin,
            Coordinate(latitude=north_lat, longitude=origin.longitude),
            Coordinate(latitude=north_lat, longitude=west_lng),
            Coordinate(latitude=south_lat, longitude=west_lng),
            Coordinate(latitude=south_lat, longitude=east_lng),
            destination,
        ]

    if route_id == "direct":
        north_lat = origin.latitude + 0.0011
        east_lng = origin.longitude + 0.0018
        south_lat = destination.latitude + 0.0002
        return [
            origin,
            Coordinate(latitude=north_lat, longitude=origin.longitude),
            Coordinate(latitude=north_lat, longitude=east_lng),
            Coordinate(latitude=south_lat, longitude=east_lng),
            Coordinate(latitude=south_lat, longitude=destination.longitude),
            destination,
        ]

    north_lat = origin.latitude + 0.0016
    east_lng = origin.longitude + 0.0007
    west_lng = destination.longitude - 0.0008
    south_lat = destination.latitude + 0.0003

    return [
        origin,
        Coordinate(latitude=north_lat, longitude=origin.longitude),
        Coordinate(latitude=north_lat, longitude=east_lng),
        Coordinate(latitude=south_lat, longitude=east_lng),
        Coordinate(latitude=south_lat, longitude=west_lng),
        destination,
    ]


def waypoints_to_segments(waypoints: list[Coordinate], crowd_level: CrowdLevel) -> list[RouteSegment]:
    return [
        RouteSegment(start=start, end=end, sensory_level=crowd_level)
        for start, end in zip(waypoints, waypoints[1:])
    ]


def apply_live_crowd_scoring(
    routes: list[RouteOption],
    sensor_locations: list[SensorLocation],
    live_counts: list[PedestrianCount],
    count_source_label: str,
) -> list[RouteOption]:
    count_by_location = {count.location_id: count for count in live_counts}
    scored_routes: list[RouteOption] = []

    for route in routes:
        nearby_counts = []

        for sensor in sensor_locations:
            count = count_by_location.get(sensor.location_id or sensor.sensor_id)
            if count is None:
                continue

            sensor_point = Coordinate(latitude=sensor.latitude, longitude=sensor.longitude)
            if is_sensor_near_route(sensor_point, route.segments, max_distance_m=420):
                nearby_counts.append(count)

        if not nearby_counts:
            scored_routes.append(route)
            continue

        max_count = max(count.total_of_directions for count in nearby_counts)
        avg_count = round(
            sum(count.total_of_directions for count in nearby_counts) / len(nearby_counts)
        )
        sensory_level = classify_crowd_count(max_count)
        high_count = sum(1 for count in nearby_counts if count.crowd_level == CrowdLevel.HIGH)
        medium_count = sum(1 for count in nearby_counts if count.crowd_level == CrowdLevel.MEDIUM)

        coverage = "partial" if len(nearby_counts) < 3 else "strong"
        reason = (
            f"Based on {len(nearby_counts)} nearby live sensor readings; "
            f"maximum recent count is {max_count} pedestrians per minute."
        )

        scored_routes.append(
            route.model_copy(
                update={
                    "sensory_level": sensory_level,
                    "sensory_level_rank": threshold_rank(sensory_level),
                    "high_congestion_segments": high_count,
                    "medium_congestion_segments": medium_count,
                    "sensor_coverage": coverage,
                    "matched_sensor_count": len(nearby_counts),
                    "average_pedestrian_count": avg_count,
                    "max_pedestrian_count": max_count,
                    "data_source": count_source_label,
                    "recommendation_reason": reason,
                    "segments": [
                        segment.model_copy(update={"sensory_level": sensory_level})
                        for segment in route.segments
                    ],
                }
            )
        )

    return scored_routes


def is_sensor_near_route(
    sensor: Coordinate,
    segments: list[RouteSegment],
    max_distance_m: int,
) -> bool:
    return any(
        distance_point_to_segment_m(sensor, segment.start, segment.end) <= max_distance_m
        for segment in segments
    )


def distance_point_to_segment_m(point: Coordinate, start: Coordinate, end: Coordinate) -> float:
    x_scale = 88_000
    y_scale = 111_000
    px = point.longitude * x_scale
    py = point.latitude * y_scale
    sx = start.longitude * x_scale
    sy = start.latitude * y_scale
    ex = end.longitude * x_scale
    ey = end.latitude * y_scale

    dx = ex - sx
    dy = ey - sy

    if dx == 0 and dy == 0:
        return haversine_m(point, start)

    t = max(0, min(1, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
    nearest = Coordinate(
        latitude=(sy + t * dy) / y_scale,
        longitude=(sx + t * dx) / x_scale,
    )
    return haversine_m(point, nearest)


def build_reason(crowd_level: CrowdLevel, high_segments: int, medium_segments: int) -> str:
    if crowd_level == CrowdLevel.LOW:
        return "Recommended because it avoids high-congestion assumptions and keeps medium segments low."
    if crowd_level == CrowdLevel.MEDIUM:
        return f"Uses a practical path with {medium_segments} medium-congestion segment assumptions."
    return f"Includes {high_segments} high-congestion segment assumption and should be used with caution."


def threshold_rank(level: CrowdLevel) -> int:
    return {
        CrowdLevel.LOW: 1,
        CrowdLevel.MEDIUM: 2,
        CrowdLevel.HIGH: 3,
    }[level]


def haversine_m(start: Coordinate, end: Coordinate) -> float:
    earth_radius_m = 6_371_000
    lat1 = radians(start.latitude)
    lat2 = radians(end.latitude)
    delta_lat = radians(end.latitude - start.latitude)
    delta_lon = radians(end.longitude - start.longitude)

    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(a))
