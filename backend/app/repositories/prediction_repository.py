from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import desc, extract, select
from sqlalchemy.orm import Session

from app.models.pedestrian_count import HistoricalPedestrianCount, RealtimePedestrianCount
from app.models.sensor_location import SensorLocation
from app.services.prediction_service import TimedCount, is_validated_city_source


class PredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def active_sensors(self) -> list[SensorLocation]:
        return list(
            self.db.scalars(
                select(SensorLocation).where(SensorLocation.status.in_(["A", "active", "Active"]))
            ).all()
        )

    def recent_counts(self, sensor_id: int, limit: int = 2) -> list[TimedCount]:
        rows = self.db.scalars(
            select(RealtimePedestrianCount)
            .where(RealtimePedestrianCount.sensor_id == sensor_id)
            .order_by(desc(RealtimePedestrianCount.sensed_at))
            .limit(limit)
        ).all()
        return [
            TimedCount(row.total_count, row.sensed_at)
            for row in rows
            if is_validated_city_source(row.data_source)
        ]

    def matching_historical_counts(self, sensor_id: int, target: datetime) -> list[int]:
        local_target = target.astimezone(ZoneInfo("Australia/Melbourne"))
        postgres_day_of_week = (local_target.weekday() + 1) % 7
        rows = self.db.scalars(
            select(HistoricalPedestrianCount).where(
                HistoricalPedestrianCount.sensor_id == sensor_id,
                HistoricalPedestrianCount.hour_of_day == local_target.hour,
                extract("dow", HistoricalPedestrianCount.sensing_date) == postgres_day_of_week,
            )
        ).all()
        return [int(row.total_count) for row in rows if is_validated_city_source(row.data_source)]
