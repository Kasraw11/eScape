from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.pedestrian_ingestion_service import MelbournePedestrianClient, PedestrianIngestionService


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    records = await MelbournePedestrianClient().fetch_latest()
    with SessionLocal() as db:
        try:
            stats = PedestrianIngestionService(db).ingest(records)
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "Realtime pedestrian ingestion completed: inserted=%d updated=%d skipped=%d invalid=%d",
        stats.inserted,
        stats.updated,
        stats.skipped,
        stats.invalid,
    )


if __name__ == "__main__":
    asyncio.run(run())
