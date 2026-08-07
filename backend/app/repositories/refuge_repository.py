from __future__ import annotations

from decimal import Decimal

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.point_of_interest import PointOfInterest
from app.models.refuge_feedback import RefugeFeedback


class RefugeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_candidates(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        category_label: str | None = None,
    ) -> list[PointOfInterest]:
        padding = radius_m / 111_320
        statement = select(PointOfInterest).where(
            PointOfInterest.is_sensory_refuge.is_(True),
            PointOfInterest.latitude >= Decimal(str(latitude - padding)),
            PointOfInterest.latitude <= Decimal(str(latitude + padding)),
            PointOfInterest.longitude >= Decimal(str(longitude - padding)),
            PointOfInterest.longitude <= Decimal(str(longitude + padding)),
        )
        if category_label:
            statement = statement.where(PointOfInterest.theme == category_label)
        return list(self.db.scalars(statement).all())

    def get(self, refuge_id: int) -> PointOfInterest | None:
        refuge = self.db.get(PointOfInterest, refuge_id)
        if refuge is None or not refuge.is_sensory_refuge:
            return None
        return refuge

    def create_feedback(
        self,
        refuge_id: int,
        quietness_score: int,
        crowding_level: str,
        comfort_level: str,
        comment: str | None,
        created_at: datetime,
    ) -> RefugeFeedback:
        feedback = RefugeFeedback(
            refuge_id=refuge_id,
            quietness_score=quietness_score,
            crowding_level=crowding_level,
            comfort_level=comfort_level,
            comment=comment,
            created_at=created_at,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def feedback_rows(self, refuge_id: int) -> list[tuple[int, str, str]]:
        statement = select(
            RefugeFeedback.quietness_score,
            RefugeFeedback.crowding_level,
            RefugeFeedback.comfort_level,
        ).where(RefugeFeedback.refuge_id == refuge_id)
        return [(int(row[0]), str(row[1]), str(row[2])) for row in self.db.execute(statement).all()]
