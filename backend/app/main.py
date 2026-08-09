from __future__ import annotations

import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router as routes_router
from app.api.refuges import router as refuges_router
from app.api.predictions import router as predictions_router

from app.config import settings
from app.database import Base, SessionLocal, engine

from app.repositories.pedestrian_repository import (
    PedestrianRepository,
)

from app.services.melbourne_pedestrian_service import (
    MelbournePedestrianService,
)

# Import database models so SQLAlchemy knows
# which tables need to be created.
from app.models.sensor_location import SensorLocation
from app.models.pedestrian_count import (
    HistoricalPedestrianCount,
    RealtimePedestrianCount,
)


logger = logging.getLogger(__name__)


# --------------------------------------------------
# AUTOMATIC PEDESTRIAN DATA SYNC
# --------------------------------------------------

async def pedestrian_sync_worker() -> None:
    """
    Periodically fetch the latest City of Melbourne
    pedestrian data and store it in PostgreSQL.
    """

    while True:
        try:
            if SessionLocal is None:
                logger.warning(
                    "Pedestrian sync skipped: "
                    "database unavailable."
                )

            else:
                db = SessionLocal()

                try:
                    repository = PedestrianRepository(db)

                    service = MelbournePedestrianService(
                        repository=repository,
                    )

                    result = await service.sync_to_database()

                    print(
                        "AUTO PEDESTRIAN SYNC:",
                        result,
                    )

                except Exception as exc:
                    db.rollback()

                    logger.exception(
                        "Automatic pedestrian sync failed: %s",
                        exc,
                    )

                finally:
                    db.close()

        except Exception as exc:
            logger.exception(
                "Unexpected pedestrian sync worker error: %s",
                exc,
            )

        # Refresh every 30 seconds.
        await asyncio.sleep(30)


# --------------------------------------------------
# FASTAPI LIFESPAN
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Starts background services when FastAPI starts
    and shuts them down cleanly when FastAPI stops.
    """

    sync_task = asyncio.create_task(
        pedestrian_sync_worker()
    )

    try:
        yield

    finally:
        sync_task.cancel()

        try:
            await sync_task

        except asyncio.CancelledError:
            pass


# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI(
    title="eScape API",
    description=(
        "Backend API for sensory-aware "
        "urban navigation"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# DATABASE TABLE CREATION
# --------------------------------------------------

# For development:
#
# Create database tables that do not exist yet.
#
# This does not delete existing tables or data.
#
# Later this should be replaced with Alembic
# migrations for production.

if engine is not None:
    Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.backend_cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)


# --------------------------------------------------
# API ROUTERS
# --------------------------------------------------

app.include_router(routes_router)
app.include_router(refuges_router)
app.include_router(predictions_router)


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get("/")
def read_root() -> dict[str, str]:
    """
    Basic API status endpoint.
    """

    return {
        "message": "eScape API is running",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def read_health() -> dict[str, str]:
    """
    Checks whether the FastAPI application is running.
    """

    return {
        "status": "ok",
    }


# --------------------------------------------------
# DATABASE HEALTH CHECK
# --------------------------------------------------

@app.get(
    "/health/database",
    response_model=None,
)
def read_database_health() -> dict[str, str] | JSONResponse:
    """
    Checks whether FastAPI can connect
    to the configured PostgreSQL database.
    """

    if engine is None:
        logger.warning(
            "Database health check failed: "
            "database URL is not configured"
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unavailable",
            },
        )

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

    except Exception as exc:
        logger.warning(
            "Database health check failed: %s",
            exc.__class__.__name__,
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "database": "connected",
    }