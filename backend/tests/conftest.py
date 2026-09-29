"""Shared pytest fixtures for migration runner tests.

These tests require a running Postgres reachable via DATABASE_URL (defaults to
the local docker-compose instance). Each test runs against isolated table
names / a temp migrations dir and cleans up after itself.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/backend",
)

# Tables that tests may create; dropped before and after each test to keep the
# runs isolated and idempotent.
_TEST_TABLES = ("schema_migrations", "users", "widgets")


async def _drop_test_objects(conn: asyncpg.Connection) -> None:
    for table in _TEST_TABLES:
        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


@pytest_asyncio.fixture
async def conn() -> AsyncIterator[asyncpg.Connection]:
    connection = await asyncpg.connect(dsn=DATABASE_URL)
    await _drop_test_objects(connection)
    try:
        yield connection
    finally:
        await _drop_test_objects(connection)
        await connection.close()


@pytest.fixture
def migrations_dir(tmp_path):
    """A fresh, empty migrations directory per test."""
    d = tmp_path / "migrations"
    d.mkdir()
    return d
