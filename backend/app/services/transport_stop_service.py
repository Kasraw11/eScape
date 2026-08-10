from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models.transport_stop import TransportStop
from app.services.routing_models import RouteCandidate


DEFAULT_MAX_DISTANCE_M = 120

# If two train records are within this distance,
# treat them as the same station for the MVP.
TRAIN_DUPLICATE_DISTANCE_M = 40


# Internal railway features that are not useful as
# public transport access-point markers for the MVP.
IGNORED_TRAIN_NAME_KEYWORDS = (
    "lift",
    "concourse",
    "decision point",
    "connex",
    " dp",
    "replacement bus",
)


IGNORED_TRAIN_ID_PARTS = (
    "_LI",
    "_DP",
    "_sDP",
    "_mDP",
    "_CN",
    "_sCN",
    "_mCN",
    "_ConX",
    "_EN",
    "_sEN",
    "_eEN",
    "_dEN",
    "_yEN",
    "_mEN",
)


def haversine_distance_m(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculates the straight-line distance between
    two latitude/longitude coordinates in metres.
    """

    earth_radius_m = 6_371_000

    lat1 = radians(latitude_1)
    lon1 = radians(longitude_1)
    lat2 = radians(latitude_2)
    lon2 = radians(longitude_2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * asin(sqrt(a))

    return earth_radius_m * c


def should_include_stop(
    stop: TransportStop,
) -> bool:
    """
    Returns True when the transport stop should be
    shown as an access point in the eScape MVP.

    Train datasets can contain internal station features
    such as lifts, concourses and decision points.
    These are ignored for route-level transport access.
    """

    if stop.mode != "train":
        return True

    stop_name = (
        stop.stop_name
        or ""
    ).lower()

    stop_id = (
        stop.stop_id
        or ""
    )

    for keyword in IGNORED_TRAIN_NAME_KEYWORDS:
        if keyword in stop_name:
            return False

    for id_part in IGNORED_TRAIN_ID_PARTS:
        if id_part.lower() in stop_id.lower():
            return False

    return True


def closest_route_point(
    stop: TransportStop,
    route_points: list[tuple[float, float]],
) -> tuple[float, int] | None:
    """
    Finds the closest route point to a transport stop.

    Returns:
        (
            distance_from_route_m,
            closest_route_point_index
        )
    """

    if not route_points:
        return None

    stop_latitude = float(
        stop.latitude
    )

    stop_longitude = float(
        stop.longitude
    )

    best_distance: float | None = None
    best_index = 0

    for index, (
        route_latitude,
        route_longitude,
    ) in enumerate(route_points):

        distance_m = haversine_distance_m(
            stop_latitude,
            stop_longitude,
            route_latitude,
            route_longitude,
        )

        if (
            best_distance is None
            or distance_m < best_distance
        ):
            best_distance = distance_m
            best_index = index

    if best_distance is None:
        return None

    return best_distance, best_index


def normalised_stop_name(
    stop: TransportStop,
) -> str:
    """
    Creates a simple key used to reduce duplicate
    transport-stop records in the route response.
    """

    name = (
        stop.stop_name
        or ""
    ).strip().lower()

    return " ".join(
        name.split()
    )


def distance_between_stops_m(
    stop_1: TransportStop,
    stop_2: TransportStop,
) -> float:
    """
    Calculates the geographic distance between
    two transport-stop records.
    """

    return haversine_distance_m(
        float(stop_1.latitude),
        float(stop_1.longitude),
        float(stop_2.latitude),
        float(stop_2.longitude),
    )


def preferred_train_stop(
    stop_1: tuple[TransportStop, int, int],
    stop_2: tuple[TransportStop, int, int],
) -> tuple[TransportStop, int, int]:
    """
    Chooses which train record should represent a station.

    Preference:
    1. Prefer canonical vic:rail: records.
    2. Otherwise keep whichever is closer to the route.
    """

    first_stop = stop_1[0]
    second_stop = stop_2[0]

    first_is_vic_rail = (
        first_stop.stop_id.startswith(
            "vic:rail:"
        )
    )

    second_is_vic_rail = (
        second_stop.stop_id.startswith(
            "vic:rail:"
        )
    )

    if (
        first_is_vic_rail
        and not second_is_vic_rail
    ):
        return stop_1

    if (
        second_is_vic_rail
        and not first_is_vic_rail
    ):
        return stop_2

    if stop_1[1] <= stop_2[1]:
        return stop_1

    return stop_2


def deduplicate_train_stops(
    stops: list[
        tuple[
            TransportStop,
            int,
            int,
        ]
    ],
) -> list[
    tuple[
        TransportStop,
        int,
        int,
    ]
]:
    """
    Removes duplicate train-station records that are
    geographically very close to each other.

    Bus and tram stops are left unchanged.
    """

    non_train_stops = [
        item
        for item in stops
        if item[0].mode != "train"
    ]

    train_stops = [
        item
        for item in stops
        if item[0].mode == "train"
    ]

    unique_train_stops: list[
        tuple[
            TransportStop,
            int,
            int,
        ]
    ] = []

    for candidate in train_stops:
        duplicate_index: int | None = None

        for index, existing in enumerate(
            unique_train_stops
        ):
            distance_m = (
                distance_between_stops_m(
                    candidate[0],
                    existing[0],
                )
            )

            if (
                distance_m
                <= TRAIN_DUPLICATE_DISTANCE_M
            ):
                duplicate_index = index
                break

        if duplicate_index is None:
            unique_train_stops.append(
                candidate
            )
            continue

        existing = (
            unique_train_stops[
                duplicate_index
            ]
        )

        unique_train_stops[
            duplicate_index
        ] = preferred_train_stop(
            existing,
            candidate,
        )

    return (
        non_train_stops
        + unique_train_stops
    )


def find_transport_stops_near_route(
    db: Session,
    route: RouteCandidate,
    max_distance_m: int = DEFAULT_MAX_DISTANCE_M,
) -> list[tuple[TransportStop, int]]:
    """
    Returns useful Melbourne CBD transport stops close
    to the supplied walking route.

    Results are ordered approximately by where the stop
    appears along the walking route.

    Each result contains:
        (
            TransportStop,
            distance_from_route_m
        )
    """

    if not route.points:
        return []

    transport_stops = (
        db.query(TransportStop)
        .all()
    )

    nearby_stops: list[
        tuple[
            TransportStop,
            int,
            int,
        ]
    ] = []

    for stop in transport_stops:

        # Remove internal railway navigation features.
        if not should_include_stop(stop):
            continue

        match = closest_route_point(
            stop=stop,
            route_points=route.points,
        )

        if match is None:
            continue

        distance_m, route_point_index = match

        if distance_m > max_distance_m:
            continue

        nearby_stops.append(
            (
                stop,
                round(distance_m),
                route_point_index,
            )
        )

    # --------------------------------------------------------------
    # 1. Remove exact-name duplicates.
    # --------------------------------------------------------------

    deduplicated: dict[
        tuple[str, str],
        tuple[
            TransportStop,
            int,
            int,
        ],
    ] = {}

    for (
        stop,
        distance_m,
        route_point_index,
    ) in nearby_stops:

        key = (
            stop.mode,
            normalised_stop_name(stop),
        )

        existing = deduplicated.get(
            key
        )

        if existing is None:
            deduplicated[key] = (
                stop,
                distance_m,
                route_point_index,
            )

            continue

        existing_distance = (
            existing[1]
        )

        if distance_m < existing_distance:
            deduplicated[key] = (
                stop,
                distance_m,
                route_point_index,
            )

    cleaned_stops = list(
        deduplicated.values()
    )

    # --------------------------------------------------------------
    # 2. Remove nearby duplicate train-station records.
    # --------------------------------------------------------------

    cleaned_stops = (
        deduplicate_train_stops(
            cleaned_stops
        )
    )

    # --------------------------------------------------------------
    # 3. Sort according to position along the route.
    # --------------------------------------------------------------

    cleaned_stops.sort(
        key=lambda item: (
            item[2],
            item[1],
        )
    )

    return [
        (
            stop,
            distance_m,
        )
        for (
            stop,
            distance_m,
            _route_point_index,
        )
        in cleaned_stops
    ]