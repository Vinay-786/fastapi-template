"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load variables from a local .env file if present (no-op in production
# where env vars are injected by the platform).
load_dotenv()

# Values that count as "true" for boolean env vars (case-insensitive).
_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def to_sync_url(url: str) -> str:
    """Convert an async Postgres DSN to a sync SQLAlchemy URL for Alembic.

    The app connects with asyncpg (``postgresql://``), while Alembic runs on
    a short-lived synchronous SQLAlchemy engine using psycopg v3
    (``postgresql+psycopg://``). This helper performs that conversion so
    both sides share a single ``DATABASE_URL`` env var.
    """
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


class Settings:
    """Runtime settings sourced from the environment."""

    def __init__(self) -> None:
        # Debug mode: enables FastAPI debug + interactive API docs. Should be
        # off in production. Defaults to False (production-safe).
        self.debug: bool = _env_bool("DEBUG", default=False)

        self.database_url: str = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/backend",
        )
        # asyncpg pool sizing.
        self.db_pool_min_size: int = int(os.environ.get("DB_POOL_MIN_SIZE", "1"))
        self.db_pool_max_size: int = int(os.environ.get("DB_POOL_MAX_SIZE", "10"))

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL (psycopg) derived from DATABASE_URL.

        Used by Alembic only; the application itself stays on asyncpg.
        """
        return to_sync_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
