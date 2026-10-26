"""Shared fixtures: migrate pointpilot_test once per run, then give each test a rolled-back session."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.settings import settings

# alembic.ini lives in api/, one folder up from tests/.
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def require_url(url: str | None, env_name: str) -> str:
    if url is None:
        pytest.exit(f"{env_name} is not set. Copy it from .env.example into api/.env.", returncode=1)
    return url


@pytest.fixture(scope="session")
def app_engine() -> Iterator[Engine]:
    """Rebuild the test schema with the real migrations, then connect as the app role."""
    owner_engine = create_engine(
        require_url(settings.test_migration_database_url, "TEST_MIGRATION_DATABASE_URL")
    )
    alembic_cfg = Config(ALEMBIC_INI)

    # engine.begin() commits when the block ends; env.py leaves committing to us.
    with owner_engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        # Down to empty first, so every run starts clean and the downgrade path is exercised too.
        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")
    owner_engine.dispose()

    # Tests connect as pointpilot_app, so they run with the API's grants, not the owner's.
    engine = create_engine(require_url(settings.test_database_url, "TEST_DATABASE_URL"))
    yield engine
    engine.dispose()


@pytest.fixture
def db(app_engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after each test, so tests never see each other's rows."""
    with app_engine.connect() as connection:
        transaction = connection.begin()
        # commit() and rollback() inside a test act on a savepoint, never on the outer transaction.
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()
