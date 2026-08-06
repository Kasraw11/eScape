from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RouteSegment(Base):
    __tablename__ = "route_segment"
    __table_args__ = (
        UniqueConstraint("route_id", "segment_sequence", name="uq_route_segment_route_id_segment_sequence"),
        Index("ix_route_segment_route_id", "route_id"),
        Index("ix_route_segment_route_id_segment_sequence", "route_id", "segment_sequence"),
    )

    route_segment_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_option.route_id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    encoded_polyline: Mapped[str | None] = mapped_column(Text)
    distance_m: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    congestion_level: Mapped[str | None] = mapped_column(String(20))
    sensory_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    data_availability_status: Mapped[str | None] = mapped_column(String(30))

    route_option: Mapped["RouteOption"] = relationship(
        "RouteOption",
        back_populates="route_segments",
    )
    sensor_scores: Mapped[list["RouteSensorScore"]] = relationship(
        "RouteSensorScore",
        back_populates="route_segment",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="route_segment",
    )
