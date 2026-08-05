import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="eScape API",
    description="Backend API for sensory-aware urban navigation",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "eScape API is running"}


@app.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database")
def read_database_health() -> dict[str, str] | JSONResponse:
    if engine is None:
        logger.warning("Database health check failed: database URL is not configured")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(
            "Database health check failed: %s",
            exc.__class__.__name__,
        )
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )

    return {"status": "ok", "database": "connected"}
