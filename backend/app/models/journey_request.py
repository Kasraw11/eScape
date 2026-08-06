from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JourneyRequest(Base):
    __tablename__ = "journey_request"
    __table_args__ = (
        CheckConstraint("origin_latitude BETWEEN -90 AND 90", name="ck_journey_request_origin_latitude_range"),
        CheckConstraint("origin_longitude BETWEEN -180 AND 180", name="ck_journey_request_origin_longitude_range"),
        CheckConstraint(
            "destination_latitude BETWEEN -90 AND 90",
            name="ck_journey_request_destination_latitude_range",
        ),
        CheckConstraint(
            "destination_longitude BETWEEN -180 AND 180",
            name="ck_journey_request_destination_longitude_range",
        ),
        Index("ix_journey_request_preference_id", "preference_id"),
    )

    journey_request_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    preference_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_preference.preference_id", ondelete="RESTRICT"),
    )
    origin_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    origin_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    destination_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    destination_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    travel_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user_preference: Mapped["UserPreference | None"] = relationship(
        "UserPreference",
        back_populates="journey_requests",
    )
    route_options: Mapped[list["RouteOption"]] = relationship(
        "RouteOption",
        back_populates="journey_request",
        cascade="all, delete-orphan",
    )
