"""Typed configuration, read from environment variables or api/.env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# api/.env, found relative to this file so it loads no matter which folder you run from.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # The API connects as pointpilot_app, which has no UPDATE or DELETE on ledger_events.
    database_url: str
    # Alembic connects as pointpilot_owner, which owns the schema.
    migration_database_url: str

    # Same two roles, pointed at pointpilot_test. Only pytest reads these, so the API starts without them.
    test_database_url: str | None = None
    test_migration_database_url: str | None = None


settings = Settings()
