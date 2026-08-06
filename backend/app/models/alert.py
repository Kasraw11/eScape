from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        Index("ix_alert_route_id", "route_id"),
        Index("ix_alert_route_segment_id", "route_segment_id"),
        Index("ix_alert_sensor_id", "sensor_id"),
        Index("ix_alert_route_id_status_created_at", "route_id", "status", "created_at"),
    )

    alert_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_option.route_id", ondelete="CASCADE"),
        nullable=False,
    )
    route_segment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("route_segment.route_segment_id", ondelete="SET NULL"),
    )
    sensor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sensor_location.sensor_id", ondelete="RESTRICT"),
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    route_option: Mapped["RouteOption"] = relationship(
        "RouteOption",
        back_populates="alerts",
    )
    route_segment: Mapped["RouteSegment | None"] = relationship(
        "RouteSegment",
        back_populates="alerts",
    )
    sensor_location: Mapped["SensorLocation | None"] = relationship(
        "SensorLocation",
        back_populates="alerts",
    )
