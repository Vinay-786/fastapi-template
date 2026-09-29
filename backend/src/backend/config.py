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


@lru_cache
def get_settings() -> Settings:
    return Settings()
