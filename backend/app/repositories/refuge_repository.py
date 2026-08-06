from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.point_of_interest import PointOfInterest


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
