from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import minute-level Melbourne pedestrian count records.")
    parser.add_argument(
        "--max-records",
        type=int,
        default=5000,
        help="Maximum number of latest records to fetch from the Open Data API.",
    )
    return parser.parse_args()


async def run(max_records: int) -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    records = await MelbournePedestrianClient().fetch_records(max_records=max_records)
    with SessionLocal() as db:
        try:
            stats = PedestrianIngestionService(db).ingest(records)
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "Realtime pedestrian history ingestion completed: fetched=%d inserted=%d updated=%d skipped=%d invalid=%d",
        len(records),
        stats.inserted,
        stats.updated,
        stats.skipped,
        stats.invalid,
    )


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.max_records))
