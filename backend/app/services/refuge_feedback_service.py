from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.refuge_repository import RefugeRepository
from app.schemas.refuges import RefugeFeedbackCreate, RefugeFeedbackCreated, RefugeFeedbackSummary


class RefugeNotFoundError(LookupError):
    pass


class RefugeFeedbackService:
    def __init__(self, repository: RefugeRepository) -> None:
        self.repository = repository

    def submit(self, refuge_id: int, payload: RefugeFeedbackCreate) -> RefugeFeedbackCreated:
        if self.repository.get(refuge_id) is None:
            raise RefugeNotFoundError
        comment = payload.comment.strip() if payload.comment else None
        feedback = self.repository.create_feedback(
            refuge_id=refuge_id,
            quietness_score=payload.quietness_score,
            crowding_level=payload.crowding_level.value,
            comfort_level=payload.comfort_level.value,
            comment=comment or None,
            created_at=datetime.now(timezone.utc),
        )
        return RefugeFeedbackCreated(
            feedback_id=feedback.feedback_id,
            refuge_id=feedback.refuge_id,
            created_at=feedback.created_at,
        )

    def summary(self, refuge_id: int) -> RefugeFeedbackSummary:
        if self.repository.get(refuge_id) is None:
            raise RefugeNotFoundError
        rows = self.repository.feedback_rows(refuge_id)
        count = len(rows)
        if not count:
            return RefugeFeedbackSummary(
                refuge_id=refuge_id,
                response_count=0,
                crowding_distribution={"low": 0, "moderate": 0, "high": 0},
            )

        quietness = [row[0] for row in rows]
        crowding = [row[1] for row in rows]
        comfort = [row[2] for row in rows]
        distribution = {level: crowding.count(level) for level in ("low", "moderate", "high")}
        def percentage(matching: int) -> int:
            return round(matching * 100 / count)

        return RefugeFeedbackSummary(
            refuge_id=refuge_id,
            response_count=count,
            average_quietness=round(sum(quietness) / count, 1),
            quiet_percentage=percentage(sum(score >= 4 for score in quietness)),
            comfortable_percentage=percentage(comfort.count("yes")),
            low_crowding_percentage=percentage(crowding.count("low")),
            crowding_distribution=distribution,
        )
