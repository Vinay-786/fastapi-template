"""Shared pytest fixtures for Alembic migration tests.

These tests require a running Postgres reachable via DATABASE_URL (defaults to
the local docker-compose instance). Each test starts from a clean slate by
dropping the Alembic version table and test tables.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic.config import Config as AlembicConfig
from pytest_asyncio import fixture as async_fixture

from backend.config import to_sync_url

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/backend",
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Tables that tests may create; dropped before and after each test to keep the
# runs isolated and idempotent. Dropping alembic_version resets Alembic state
# to "base".
_TEST_TABLES = ("alembic_version", "users")


async def _drop_test_objects(conn: asyncpg.Connection) -> None:
    for table in _TEST_TABLES:
        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


@async_fixture
async def conn() -> AsyncIterator[asyncpg.Connection]:
    connection = await asyncpg.connect(dsn=DATABASE_URL)
    await _drop_test_objects(connection)
    try:
        yield connection
    finally:
        await _drop_test_objects(connection)
        await connection.close()


@pytest.fixture
def alembic_cfg() -> AlembicConfig:
    """Alembic Config with absolute paths and a sync URL for tests."""
    ini_path = BACKEND_ROOT / "alembic.ini"
    cfg = AlembicConfig(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", to_sync_url(DATABASE_URL))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg
