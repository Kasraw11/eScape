from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JourneyFeedback(Base):
    __tablename__ = "journey_feedback"
    __table_args__ = (
        CheckConstraint("sensory_rating BETWEEN 1 AND 5", name="ck_journey_feedback_sensory_rating_range"),
        CheckConstraint(
            "crowd_rating IS NULL OR crowd_rating BETWEEN 1 AND 5",
            name="ck_journey_feedback_crowd_rating_range",
        ),
        Index("ix_journey_feedback_route_id", "route_id"),
        Index("ix_journey_feedback_route_id_submitted_at", "route_id", "submitted_at"),
    )

    feedback_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_option.route_id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sensory_rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    crowd_rating: Mapped[int | None] = mapped_column(SmallInteger)
    comments: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    route_option: Mapped["RouteOption"] = relationship(
        "RouteOption",
        back_populates="journey_feedback",
    )
