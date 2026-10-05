"""Database layer: asyncpg connection pool, lifespan management, and migrations.

No ORM is used — the pool is created directly with asyncpg and all queries
are raw SQL. Schema migrations are applied with Alembic (synchronous
SQLAlchemy + psycopg engine, hand-written ``op.execute()`` revisions, no
model metadata) at startup via ``alembic upgrade head``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg

from .config import get_settings


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
        """Apply pending Alembic migrations (``upgrade head``).

        Alembic is synchronous, so the upgrade runs in a worker thread on a
        short-lived sync engine (psycopg). The ``DATABASE_URL`` env var is
        shared: it is converted to a ``postgresql+psycopg://`` URL for the
        migration engine while the app itself keeps using asyncpg.
        """
        from alembic import command as alembic_command
        from alembic.config import Config as AlembicConfig

        settings = get_settings()
        dsn_sync = settings.sync_database_url
        ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"

        def _upgrade() -> None:
            cfg = AlembicConfig(str(ini_path))
            cfg.set_main_option("sqlalchemy.url", dsn_sync)
            # Resolve relative to the ini file, not the process CWD, so
            # startup upgrades work regardless of where uvicorn was launched.
            cfg.set_main_option(
                "script_location", str(ini_path.parent / "alembic")
            )
            alembic_command.upgrade(cfg, "head")

        await asyncio.to_thread(_upgrade)

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
