from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.pedestrian_count import (
    HistoricalPedestrianCount,
    RealtimePedestrianCount,
)
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
    def __init__(
        self,
        db: Session | None,
    ) -> None:
        self.db = db

    # -------------------------------------------------
    # READ SENSOR LOCATIONS
    # -------------------------------------------------

    def get_sensors_in_bounds(
        self,
        min_latitude: float,
        max_latitude: float,
        min_longitude: float,
        max_longitude: float,
    ) -> list[SensorRecord]:
        """
        Return sensors located inside a geographic box.
        """

        if self.db is None:
            return []

        sensors = self.db.scalars(
            select(SensorLocation).where(
                SensorLocation.latitude
                >= Decimal(str(min_latitude)),
                SensorLocation.latitude
                <= Decimal(str(max_latitude)),
                SensorLocation.longitude
                >= Decimal(str(min_longitude)),
                SensorLocation.longitude
                <= Decimal(str(max_longitude)),
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

    # -------------------------------------------------
    # SAVE / UPDATE SENSOR LOCATION
    # -------------------------------------------------

    def upsert_sensor(
        self,
        sensor_id: int,
        sensor_name: str,
        latitude: float,
        longitude: float,
        *,
        status: str = "active",
        source: str = "City of Melbourne",
        last_updated_at: datetime | None = None,
    ) -> SensorLocation | None:
        """
        Create a sensor when it does not exist.

        If the sensor already exists, update its
        name, coordinates and metadata.
        """

        if self.db is None:
            return None

        sensor = self.db.get(
            SensorLocation,
            sensor_id,
        )

        if sensor is None:
            sensor = SensorLocation(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                latitude=Decimal(str(latitude)),
                longitude=Decimal(str(longitude)),
                status=status,
                source=source,
                last_updated_at=last_updated_at,
            )

            self.db.add(sensor)

        else:
            sensor.sensor_name = sensor_name
            sensor.latitude = Decimal(
                str(latitude)
            )
            sensor.longitude = Decimal(
                str(longitude)
            )
            sensor.status = status
            sensor.source = source

            if last_updated_at is not None:
                sensor.last_updated_at = (
                    last_updated_at
                )

        return sensor

    # -------------------------------------------------
    # SAVE REALTIME PEDESTRIAN COUNT
    # -------------------------------------------------

    def add_realtime_count(
        self,
        sensor_id: int,
        sensed_at: datetime,
        total_count: int,
        *,
        direction_1_count: int | None = None,
        direction_2_count: int | None = None,
        source_record_id: str | None = None,
        data_source: str = "City of Melbourne",
    ) -> bool:
        """
        Save one realtime pedestrian reading.

        Returns True when a new reading is inserted.

        Returns False if that sensor/timestamp reading
        is already stored.
        """

        if self.db is None:
            return False

        existing = self.db.scalar(
            select(RealtimePedestrianCount)
            .where(
                RealtimePedestrianCount.sensor_id
                == sensor_id,
                RealtimePedestrianCount.sensed_at
                == sensed_at,
            )
            .limit(1)
        )

        if existing is not None:
            return False

        realtime_count = RealtimePedestrianCount(
            sensor_id=sensor_id,
            sensed_at=sensed_at,
            direction_1_count=direction_1_count,
            direction_2_count=direction_2_count,
            total_count=total_count,
            source_record_id=source_record_id,
            data_source=data_source,
        )

        self.db.add(realtime_count)

        return True

    # -------------------------------------------------
    # READ LATEST PEDESTRIAN COUNTS
    # -------------------------------------------------

    def get_latest_counts(
        self,
        sensor_ids: list[int],
    ) -> dict[int, PedestrianCountRecord]:
        """
        Return the most recent count for each sensor.

        Realtime data is preferred. Historical data
        is used as a fallback.
        """

        if self.db is None or not sensor_ids:
            return {}

        counts: dict[
            int,
            PedestrianCountRecord,
        ] = {}

        for sensor_id in sensor_ids:
            realtime = self.db.scalar(
                select(RealtimePedestrianCount)
                .where(
                    RealtimePedestrianCount.sensor_id
                    == sensor_id
                )
                .order_by(
                    desc(
                        RealtimePedestrianCount.sensed_at
                    )
                )
                .limit(1)
            )

            if realtime is not None:
                counts[sensor_id] = (
                    PedestrianCountRecord(
                        sensor_id=sensor_id,
                        total_count=realtime.total_count,
                        observed_at=realtime.sensed_at,
                        source="realtime",
                    )
                )

                continue

            historical = self.db.scalar(
                select(HistoricalPedestrianCount)
                .where(
                    HistoricalPedestrianCount.sensor_id
                    == sensor_id
                )
                .order_by(
                    desc(
                        HistoricalPedestrianCount.sensing_date
                    ),
                    desc(
                        HistoricalPedestrianCount.hour_of_day
                    ),
                )
                .limit(1)
            )

            if historical is not None:
                counts[sensor_id] = (
                    PedestrianCountRecord(
                        sensor_id=sensor_id,
                        total_count=historical.total_count,
                        observed_at=historical.sensing_date,
                        source="historical",
                    )
                )

        return counts

    # -------------------------------------------------
    # HISTORICAL BASELINES
    # -------------------------------------------------

    def get_historical_baselines(
        self,
        sensor_ids: list[int],
    ) -> dict[int, float]:
        """
        Return the historical average pedestrian
        count for each requested sensor.
        """

        if self.db is None or not sensor_ids:
            return {}

        rows = self.db.execute(
            select(
                HistoricalPedestrianCount.sensor_id,
                func.avg(
                    HistoricalPedestrianCount.total_count
                ),
            )
            .where(
                HistoricalPedestrianCount.sensor_id.in_(
                    sensor_ids
                )
            )
            .group_by(
                HistoricalPedestrianCount.sensor_id
            )
        ).all()

        return {
            int(sensor_id): float(average)
            for sensor_id, average in rows
            if average is not None
            and float(average) > 0
        }

    # -------------------------------------------------
    # TRANSACTION HELPERS
    # -------------------------------------------------

    def commit(self) -> None:
        """
        Save pending database changes.
        """

        if self.db is not None:
            self.db.commit()

    def rollback(self) -> None:
        """
        Roll back pending database changes.
        """

        if self.db is not None:
            self.db.rollback()