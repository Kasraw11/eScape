from __future__ import annotations

import math
from dataclasses import dataclass

from app.repositories.pedestrian_repository import SensorRecord
from app.services.google_maps_service import RouteSegmentCandidate


MATCHING_DISTANCE_M = 150
DEGREES_PER_METER = 1 / 111_320


@dataclass(frozen=True)
class MatchedSensor:
    sensor: SensorRecord
    distance_m: float
    route_point_index: int


@dataclass(frozen=True)
class SegmentSensorMatch:
    segment_sequence: int
    matched_sensors: list[MatchedSensor]
    distance_m: int | None = None


def haversine_meters(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = first
    lat2, lon2 = second
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def route_bounds(points: list[tuple[float, float]], padding_m: int = MATCHING_DISTANCE_M) -> tuple[float, float, float, float]:
    if not points:
        return (-90, 90, -180, 180)
    padding_degrees = padding_m * DEGREES_PER_METER
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    return (
        min(latitudes) - padding_degrees,
        max(latitudes) + padding_degrees,
        min(longitudes) - padding_degrees,
        max(longitudes) + padding_degrees,
    )


class SensorMatchingService:
    def __init__(self, matching_distance_m: int = MATCHING_DISTANCE_M) -> None:
        self.matching_distance_m = matching_distance_m

    def match_segment(
        self,
        segment: RouteSegmentCandidate,
        sensors: list[SensorRecord],
    ) -> SegmentSensorMatch:
        matches_by_sensor: dict[int, MatchedSensor] = {}
        if not segment.points:
            return SegmentSensorMatch(segment_sequence=segment.segment_sequence, matched_sensors=[], distance_m=segment.distance_m)

        for sensor in sensors:
            nearest_index = 0
            nearest_distance = math.inf
            for index, point in enumerate(segment.points):
                distance = haversine_meters(point, (sensor.latitude, sensor.longitude))
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_index = index

            if nearest_distance <= self.matching_distance_m:
                matches_by_sensor[sensor.sensor_id] = MatchedSensor(
                    sensor=sensor,
                    distance_m=nearest_distance,
                    route_point_index=nearest_index,
                )

        return SegmentSensorMatch(
            segment_sequence=segment.segment_sequence,
            matched_sensors=sorted(
                matches_by_sensor.values(),
                key=lambda match: (match.route_point_index, match.distance_m),
            ),
            distance_m=segment.distance_m,
        )
