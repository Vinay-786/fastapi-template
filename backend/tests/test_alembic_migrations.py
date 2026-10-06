"""Tests for Alembic migrations (no ORM, hand-written raw SQL revisions)."""

from __future__ import annotations

import pytest
from alembic.script import ScriptDirectory

from alembic import command as alembic_command
from backend.config import to_sync_url


def _current_revisions(cfg) -> list[str]:
    script = ScriptDirectory.from_config(cfg)
    # Heads available on disk, for sanity checks.
    return list(script.get_heads())


async def _table_exists(conn, table: str) -> bool:
    return await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)


async def _db_version(conn) -> str | None:
    if not await _table_exists(conn, "alembic_version"):
        return None
    return await conn.fetchval("SELECT version_num FROM alembic_version")


def test_to_sync_url_conversion():
    assert (
        to_sync_url("postgresql://user:pass@localhost:5432/backend")
        == "postgresql+psycopg://user:pass@localhost:5432/backend"
    )
    assert (
        to_sync_url("postgresql+asyncpg://user:pass@localhost:5432/backend")
        == "postgresql+psycopg://user:pass@localhost:5432/backend"
    )
    # Already sync URLs pass through untouched.
    sync = "postgresql+psycopg://user:pass@localhost:5432/backend"
    assert to_sync_url(sync) == sync


def test_single_head_exists(alembic_cfg):
    assert _current_revisions(alembic_cfg) == ["0001"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_upgrade_head_creates_users(conn, alembic_cfg):
    alembic_command.upgrade(alembic_cfg, "head")

    assert await _db_version(conn) == "0001"
    assert await _table_exists(conn, "users")

    # The schema matches the original contract: insert a row via asyncpg.
    row = await conn.fetchrow(
        "INSERT INTO users (email, full_name) VALUES ($1, $2)"
        " RETURNING id, email, full_name, created_at",
        "a@example.com",
        "Alice",
    )
    assert row["email"] == "a@example.com"


@pytest.mark.db
@pytest.mark.asyncio
async def test_upgrade_is_idempotent(conn, alembic_cfg):
    alembic_command.upgrade(alembic_cfg, "head")
    alembic_command.upgrade(alembic_cfg, "head")  # second run is a no-op

    assert await _db_version(conn) == "0001"
    assert await _table_exists(conn, "users")


@pytest.mark.db
@pytest.mark.asyncio
async def test_downgrade_and_reupgrade(conn, alembic_cfg):
    alembic_command.upgrade(alembic_cfg, "head")
    assert await _table_exists(conn, "users")

    alembic_command.downgrade(alembic_cfg, "-1")
    assert not await _table_exists(conn, "users")

    alembic_command.upgrade(alembic_cfg, "head")
    assert await _db_version(conn) == "0001"
    assert await _table_exists(conn, "users")


@pytest.mark.db
@pytest.mark.asyncio
async def test_startup_migrate_applies_schema(conn, alembic_cfg):
    """Database._migrate() (app startup path) brings a fresh DB to head."""
    from backend.database import Database

    # Fresh DB: nothing applied yet.
    assert not await _table_exists(conn, "users")

    db = Database()
    await db.connect()
    try:
        assert await _table_exists(conn, "users")
        assert await _db_version(conn) == "0001"
    finally:
        await db.disconnect()
