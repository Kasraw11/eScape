from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.pedestrian_count import HistoricalPedestrianCount, RealtimePedestrianCount
from app.models.sensor_location import SensorLocation


@dataclass(frozen=True)
class SensorRecord:
    sensor_id: int
    sensor_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PedestrianCountRecord:
    sensor_id: int
    total_count: int
    observed_at: datetime | date
    source: str


class PedestrianRepository:
    def __init__(self, db: Session | None) -> None:
        self.db = db

    def get_sensors_in_bounds(
        self,
        min_latitude: float,
        max_latitude: float,
        min_longitude: float,
        max_longitude: float,
    ) -> list[SensorRecord]:
        if self.db is None:
            return []

        sensors = self.db.scalars(
            select(SensorLocation).where(
                SensorLocation.latitude >= Decimal(str(min_latitude)),
                SensorLocation.latitude <= Decimal(str(max_latitude)),
                SensorLocation.longitude >= Decimal(str(min_longitude)),
                SensorLocation.longitude <= Decimal(str(max_longitude)),
            )
        ).all()

        return [
            SensorRecord(
                sensor_id=sensor.sensor_id,
                sensor_name=sensor.sensor_name,
                latitude=float(sensor.latitude),
                longitude=float(sensor.longitude),
            )
            for sensor in sensors
        ]

    def get_latest_counts(self, sensor_ids: list[int]) -> dict[int, PedestrianCountRecord]:
        if self.db is None or not sensor_ids:
            return {}

        counts: dict[int, PedestrianCountRecord] = {}
        for sensor_id in sensor_ids:
            realtime = self.db.scalar(
                select(RealtimePedestrianCount)
                .where(RealtimePedestrianCount.sensor_id == sensor_id)
                .order_by(desc(RealtimePedestrianCount.sensed_at))
                .limit(1)
            )
            if realtime is not None:
                counts[sensor_id] = PedestrianCountRecord(
                    sensor_id=sensor_id,
                    total_count=realtime.total_count,
                    observed_at=realtime.sensed_at,
                    source="realtime",
                )
                continue

            historical = self.db.scalar(
                select(HistoricalPedestrianCount)
                .where(HistoricalPedestrianCount.sensor_id == sensor_id)
                .order_by(desc(HistoricalPedestrianCount.sensing_date), desc(HistoricalPedestrianCount.hour_of_day))
                .limit(1)
            )
            if historical is not None:
                counts[sensor_id] = PedestrianCountRecord(
                    sensor_id=sensor_id,
                    total_count=historical.total_count,
                    observed_at=historical.sensing_date,
                    source="historical",
                )

        return counts

    def get_historical_baselines(self, sensor_ids: list[int]) -> dict[int, float]:
        """Return per-sensor historical means used as a coarse comparison baseline.

        The Iteration 2 API deliberately reports this as an approximation: the
        initial schema does not retain enough calendar dimensions to calculate a
        matched weekday/season baseline without introducing unsupported precision.
        """
        if self.db is None or not sensor_ids:
            return {}

        rows = self.db.execute(
            select(
                HistoricalPedestrianCount.sensor_id,
                func.avg(HistoricalPedestrianCount.total_count),
            )
            .where(HistoricalPedestrianCount.sensor_id.in_(sensor_ids))
            .group_by(HistoricalPedestrianCount.sensor_id)
        ).all()
        return {int(sensor_id): float(average) for sensor_id, average in rows if average is not None and float(average) > 0}
