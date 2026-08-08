from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RouteSensorScore(Base):
    __tablename__ = "route_sensor_score"
    __table_args__ = (
        Index("ix_route_sensor_score_route_segment_id", "route_segment_id"),
        Index("ix_route_sensor_score_sensor_id", "sensor_id"),
    )

    route_sensor_score_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_segment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_segment.route_segment_id", ondelete="CASCADE"),
        nullable=False,
    )
    sensor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sensor_location.sensor_id", ondelete="RESTRICT"),
        nullable=False,
    )
    count_source: Mapped[str] = mapped_column(String(30), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    count_used: Mapped[int | None] = mapped_column(Integer)
    score_contribution: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    route_segment: Mapped["RouteSegment"] = relationship(
        "RouteSegment",
        back_populates="sensor_scores",
    )
    sensor_location: Mapped["SensorLocation"] = relationship(
        "SensorLocation",
        back_populates="route_sensor_scores",
    )
