from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Identity, Index, Integer, SmallInteger, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserPreference(Base):
    __tablename__ = "user_preference"
    __table_args__ = (
        CheckConstraint(
            "preferred_crowd_threshold BETWEEN 1 AND 5",
            name="ck_user_preference_preferred_crowd_threshold_range",
        ),
        CheckConstraint("search_radius_m > 0", name="ck_user_preference_search_radius_m_positive"),
        Index("ix_user_preference_session_id", "session_id"),
    )

    preference_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True)
    preferred_crowd_threshold: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    search_radius_m: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    journey_requests: Mapped[list["JourneyRequest"]] = relationship(
        "JourneyRequest",
        back_populates="user_preference",
    )
