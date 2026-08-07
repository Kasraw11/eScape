from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RouteRefugeRecommendation(Base):
    __tablename__ = "route_refuge_recommendation"
    __table_args__ = (
        UniqueConstraint("route_id", "poi_id", name="uq_route_refuge_recommendation_route_id_poi_id"),
        Index("ix_route_refuge_recommendation_route_id", "route_id"),
        Index("ix_route_refuge_recommendation_poi_id", "poi_id"),
    )

    route_refuge_recommendation_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_option.route_id", ondelete="CASCADE"),
        nullable=False,
    )
    poi_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("point_of_interest.poi_id", ondelete="RESTRICT"),
        nullable=False,
    )
    recommendation_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_from_route_m: Mapped[int | None] = mapped_column(Integer)
    availability_status: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    route_option: Mapped["RouteOption"] = relationship(
        "RouteOption",
        back_populates="refuge_recommendations",
    )
    point_of_interest: Mapped["PointOfInterest"] = relationship(
        "PointOfInterest",
        back_populates="refuge_recommendations",
    )
