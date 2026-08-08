from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Index, Integer, Numeric, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RouteOption(Base):
    __tablename__ = "route_option"
    __table_args__ = (
        Index("ix_route_option_journey_request_id", "journey_request_id"),
    )

    route_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    journey_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("journey_request.journey_request_id", ondelete="CASCADE"),
        nullable=False,
    )
    google_route_id: Mapped[str | None] = mapped_column(String(255))
    encoded_polyline: Mapped[str | None] = mapped_column(Text)
    estimated_travel_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sensory_indicator: Mapped[str] = mapped_column(String(20), nullable=False)
    total_sensory_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    data_availability_status: Mapped[str] = mapped_column(String(30), nullable=False)
    is_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    journey_request: Mapped["JourneyRequest"] = relationship(
        "JourneyRequest",
        back_populates="route_options",
    )
    route_segments: Mapped[list["RouteSegment"]] = relationship(
        "RouteSegment",
        back_populates="route_option",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="route_option",
        cascade="all, delete-orphan",
    )
    refuge_recommendations: Mapped[list["RouteRefugeRecommendation"]] = relationship(
        "RouteRefugeRecommendation",
        back_populates="route_option",
        cascade="all, delete-orphan",
    )
    transport_stops: Mapped[list["RouteTransportStop"]] = relationship(
        "RouteTransportStop",
        back_populates="route_option",
        cascade="all, delete-orphan",
    )
    journey_feedback: Mapped[list["JourneyFeedback"]] = relationship(
        "JourneyFeedback",
        back_populates="route_option",
        cascade="all, delete-orphan",
    )
