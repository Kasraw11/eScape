from __future__ import annotations

import logging

from app.database import SessionLocal
from app.services.prediction_job_service import PredictionJobService


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    with SessionLocal() as db:
        try:
            stats = PredictionJobService(db).run()
            db.commit()
        except Exception:
            db.rollback()
            raise
    logger.info(
        "Prediction job completed: predictions_inserted=%d predictions_updated=%d unavailable=%d "
        "alerts_created=%d alerts_updated=%d alerts_closed=%d unchanged=%d failed=%d",
        stats.predictions_inserted,
        stats.predictions_updated,
        stats.unavailable,
        stats.alerts_created,
        stats.alerts_updated,
        stats.alerts_closed,
        stats.unchanged,
        stats.failed,
    )


if __name__ == "__main__":
    run()
