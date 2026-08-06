from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransportStop(Base):
    __tablename__ = "transport_stop"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_transport_stop_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_transport_stop_longitude_range"),
        Index("ix_transport_stop_latitude_longitude", "latitude", "longitude"),
    )

    stop_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    stop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)

    route_stops: Mapped[list["RouteTransportStop"]] = relationship(
        "RouteTransportStop",
        back_populates="transport_stop",
    )


class RouteTransportStop(Base):
    __tablename__ = "route_transport_stop"
    __table_args__ = (
        Index("ix_route_transport_stop_route_id", "route_id"),
        Index("ix_route_transport_stop_stop_id", "stop_id"),
    )

    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_option.route_id", ondelete="CASCADE"),
        primary_key=True,
    )
    stop_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("transport_stop.stop_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_role: Mapped[str | None] = mapped_column(String(30))
    distance_m: Mapped[int | None] = mapped_column(Integer)

    route_option: Mapped["RouteOption"] = relationship(
        "RouteOption",
        back_populates="transport_stops",
    )
    transport_stop: Mapped["TransportStop"] = relationship(
        "TransportStop",
        back_populates="route_stops",
    )
