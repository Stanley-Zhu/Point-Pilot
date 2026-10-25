"""Database engine and the per-request session dependency."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import settings

# One engine per process; it owns the connection pool.
engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards.

    It never commits. Services call db.commit() themselves, so each
    transaction boundary is visible in the code that owns it.
    """
    with SessionLocal() as session:
        yield session
