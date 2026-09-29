"""Database layer: asyncpg connection pool, lifespan management, and migrations.

No ORM and no migration framework are used — the pool is created directly with
asyncpg and the schema is brought up to date by the forward-only migration
runner in :mod:`backend.migrations` at startup.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from .config import get_settings
from .migrations import run_migrations


class Database:
    """Owns a single asyncpg connection pool for the app's lifetime."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Did lifespan run?")
        return self._pool

    async def connect(self) -> None:
        """Create the pool and apply the schema."""
        settings = get_settings()
        self._pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
        await self._migrate()

    async def disconnect(self) -> None:
        """Gracefully close the pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _migrate(self) -> None:
        """Apply pending forward-only migrations on a single connection.

        A dedicated connection is used so the advisory lock is held for the
        duration of the migration run and released deterministically.
        """
        async with self.connection() as conn:
            await run_migrations(conn)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a connection from the pool as an async context manager.

        Usage:
            async with db.connection() as conn:
                await conn.fetch("SELECT 1")
        """
        async with self.pool.acquire() as conn:
            yield conn


# Module-level singleton wired up by the FastAPI lifespan.
db = Database()
