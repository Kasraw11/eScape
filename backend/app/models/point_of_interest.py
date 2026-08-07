from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Identity, Index, Numeric, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PointOfInterest(Base):
    __tablename__ = "point_of_interest"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_point_of_interest_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_point_of_interest_longitude_range"),
        Index("ix_point_of_interest_latitude_longitude", "latitude", "longitude"),
        UniqueConstraint("source", "source_record_id", name="uq_point_of_interest_source_record_id"),
    )

    poi_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    theme: Mapped[str | None] = mapped_column(String(100))
    sub_theme: Mapped[str | None] = mapped_column(String(100))
    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    coordinates_text: Mapped[str | None] = mapped_column(Text)
    opening_hours: Mapped[str | None] = mapped_column(Text)
    is_sensory_refuge: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    source: Mapped[str | None] = mapped_column(String(100))
    source_record_id: Mapped[str | None] = mapped_column(String(255))
    accessibility_notes: Mapped[str | None] = mapped_column(Text)
    sensory_notes: Mapped[str | None] = mapped_column(Text)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    refuge_recommendations: Mapped[list["RouteRefugeRecommendation"]] = relationship(
        "RouteRefugeRecommendation",
        back_populates="point_of_interest",
    )
    community_feedback: Mapped[list["RefugeFeedback"]] = relationship(
        "RefugeFeedback",
        back_populates="refuge",
        cascade="all, delete-orphan",
    )
