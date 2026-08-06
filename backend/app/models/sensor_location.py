from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Identity, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SensorLocation(Base):
    __tablename__ = "sensor_location"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_sensor_location_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_sensor_location_longitude_range"),
        Index("ix_sensor_location_latitude_longitude", "latitude", "longitude"),
    )

    sensor_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sensor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(255))
    location_type: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    installation_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    direction_1: Mapped[str | None] = mapped_column(String(100))
    direction_2: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    historical_counts: Mapped[list["HistoricalPedestrianCount"]] = relationship(
        "HistoricalPedestrianCount",
        back_populates="sensor_location",
    )
    realtime_counts: Mapped[list["RealtimePedestrianCount"]] = relationship(
        "RealtimePedestrianCount",
        back_populates="sensor_location",
    )
    route_sensor_scores: Mapped[list["RouteSensorScore"]] = relationship(
        "RouteSensorScore",
        back_populates="sensor_location",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="sensor_location",
    )
