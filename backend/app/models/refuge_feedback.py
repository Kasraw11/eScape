from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RefugeFeedback(Base):
    __tablename__ = "refuge_feedback"
    __table_args__ = (
        CheckConstraint("quietness_score BETWEEN 1 AND 5", name="ck_refuge_feedback_quietness_range"),
        CheckConstraint("crowding_level IN ('low', 'moderate', 'high')", name="ck_refuge_feedback_crowding_level"),
        CheckConstraint("comfort_level IN ('yes', 'somewhat', 'no')", name="ck_refuge_feedback_comfort_level"),
        Index("ix_refuge_feedback_refuge_id", "refuge_id"),
        Index("ix_refuge_feedback_refuge_id_created_at", "refuge_id", "created_at"),
    )

    feedback_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    refuge_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("point_of_interest.poi_id", ondelete="CASCADE"),
        nullable=False,
    )
    quietness_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    crowding_level: Mapped[str] = mapped_column(String(20), nullable=False)
    comfort_level: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    refuge: Mapped["PointOfInterest"] = relationship("PointOfInterest", back_populates="community_feedback")
