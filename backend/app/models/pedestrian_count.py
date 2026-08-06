from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HistoricalPedestrianCount(Base):
    __tablename__ = "historical_pedestrian_count"
    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "sensing_date",
            "hour_of_day",
            name="uq_historical_pedestrian_count_sensor_date_hour",
        ),
        CheckConstraint("hour_of_day BETWEEN 0 AND 23", name="ck_historical_pedestrian_count_hour_of_day_range"),
        CheckConstraint(
            "direction_1_count IS NULL OR direction_1_count >= 0",
            name="ck_historical_pedestrian_count_direction_1_non_negative",
        ),
        CheckConstraint(
            "direction_2_count IS NULL OR direction_2_count >= 0",
            name="ck_historical_pedestrian_count_direction_2_non_negative",
        ),
        CheckConstraint("total_count >= 0", name="ck_historical_pedestrian_count_total_non_negative"),
        Index("ix_historical_pedestrian_count_sensor_id", "sensor_id"),
        Index(
            "ix_historical_pedestrian_count_sensor_date_hour",
            "sensor_id",
            "sensing_date",
            "hour_of_day",
        ),
    )

    historical_count_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sensor_location.sensor_id", ondelete="RESTRICT"),
        nullable=False,
    )
    sensing_date: Mapped[date] = mapped_column(Date, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    direction_1_count: Mapped[int | None] = mapped_column(Integer)
    direction_2_count: Mapped[int | None] = mapped_column(Integer)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(255))

    sensor_location: Mapped["SensorLocation"] = relationship(
        "SensorLocation",
        back_populates="historical_counts",
    )


class RealtimePedestrianCount(Base):
    __tablename__ = "realtime_pedestrian_count"
    __table_args__ = (
        CheckConstraint(
            "direction_1_count IS NULL OR direction_1_count >= 0",
            name="ck_realtime_pedestrian_count_direction_1_non_negative",
        ),
        CheckConstraint(
            "direction_2_count IS NULL OR direction_2_count >= 0",
            name="ck_realtime_pedestrian_count_direction_2_non_negative",
        ),
        CheckConstraint("total_count >= 0", name="ck_realtime_pedestrian_count_total_non_negative"),
        Index("ix_realtime_pedestrian_count_sensor_id", "sensor_id"),
        Index("ix_realtime_pedestrian_count_sensor_id_sensed_at", "sensor_id", "sensed_at"),
    )

    realtime_count_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sensor_location.sensor_id", ondelete="RESTRICT"),
        nullable=False,
    )
    sensed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    direction_1_count: Mapped[int | None] = mapped_column(Integer)
    direction_2_count: Mapped[int | None] = mapped_column(Integer)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(255))

    sensor_location: Mapped["SensorLocation"] = relationship(
        "SensorLocation",
        back_populates="realtime_counts",
    )
