from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


engine: Engine | None = (
    create_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)

SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
    if engine is not None
    else None
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
