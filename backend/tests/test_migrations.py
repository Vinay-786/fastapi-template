"""Tests for the forward-only migration runner."""

from __future__ import annotations

import asyncpg
import pytest

from backend.migrations import discover_migrations, run_migrations

pytestmark = pytest.mark.asyncio


def _write(migrations_dir, name: str, sql: str) -> None:
    (migrations_dir / name).write_text(sql, encoding="utf-8")


async def _applied(conn) -> list[str]:
    rows = await conn.fetch(
        "SELECT version FROM schema_migrations ORDER BY version"
    )
    return [r["version"] for r in rows]


async def _table_exists(conn, table: str) -> bool:
    return await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)


async def test_fresh_database_applies_0001(conn, migrations_dir):
    _write(
        migrations_dir,
        "0001_create_users.sql",
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE
        );
        """,
    )

    applied = await run_migrations(conn, migrations_dir)

    assert applied == ["0001_create_users"]
    assert await _applied(conn) == ["0001_create_users"]
    assert await _table_exists(conn, "users")


async def test_second_run_applies_nothing(conn, migrations_dir):
    _write(
        migrations_dir,
        "0001_create_users.sql",
        "CREATE TABLE users (id UUID PRIMARY KEY DEFAULT gen_random_uuid());",
    )

    first = await run_migrations(conn, migrations_dir)
    second = await run_migrations(conn, migrations_dir)

    assert first == ["0001_create_users"]
    assert second == []  # idempotent no-op
    assert await _applied(conn) == ["0001_create_users"]


async def test_adding_0002_applies_only_the_new_one(conn, migrations_dir):
    _write(
        migrations_dir,
        "0001_create_users.sql",
        "CREATE TABLE users (id UUID PRIMARY KEY DEFAULT gen_random_uuid());",
    )
    first = await run_migrations(conn, migrations_dir)
    assert first == ["0001_create_users"]

    # New migration added later.
    _write(
        migrations_dir,
        "0002_add_widgets.sql",
        "CREATE TABLE widgets (id UUID PRIMARY KEY DEFAULT gen_random_uuid());",
    )

    second = await run_migrations(conn, migrations_dir)

    assert second == ["0002_add_widgets"]  # only the new one
    assert await _applied(conn) == ["0001_create_users", "0002_add_widgets"]
    assert await _table_exists(conn, "widgets")


async def test_failed_migration_is_rolled_back_and_not_recorded(
    conn, migrations_dir
):
    _write(
        migrations_dir,
        "0001_create_users.sql",
        "CREATE TABLE users (id UUID PRIMARY KEY DEFAULT gen_random_uuid());",
    )
    # This migration creates a table then issues invalid SQL: the whole thing
    # must roll back, including the widgets table, and must NOT be recorded.
    _write(
        migrations_dir,
        "0002_broken.sql",
        """
        CREATE TABLE widgets (id UUID PRIMARY KEY DEFAULT gen_random_uuid());
        THIS IS NOT VALID SQL;
        """,
    )

    with pytest.raises(asyncpg.PostgresError):
        await run_migrations(conn, migrations_dir)

    # 0001 succeeded and is recorded; 0002 rolled back entirely.
    assert await _applied(conn) == ["0001_create_users"]
    assert await _table_exists(conn, "users")
    assert not await _table_exists(conn, "widgets")

    # The advisory lock must have been released even though the run failed,
    # so a subsequent run can proceed.
    _write(  # replace broken file with a valid one (new content, same version)
        migrations_dir,
        "0002_broken.sql",
        "CREATE TABLE widgets (id UUID PRIMARY KEY DEFAULT gen_random_uuid());",
    )
    applied = await run_migrations(conn, migrations_dir)
    assert applied == ["0002_broken"]


async def test_migrations_execute_in_version_order(conn, migrations_dir):
    # Write files out of order on disk to prove sorting, not FS order, wins.
    _write(
        migrations_dir,
        "0003_c.sql",
        "CREATE TABLE widgets (id INT PRIMARY KEY);",
    )
    _write(
        migrations_dir,
        "0001_a.sql",
        "CREATE TABLE users (id INT PRIMARY KEY);",
    )
    _write(
        migrations_dir,
        "0002_b.sql",
        "ALTER TABLE users ADD COLUMN name TEXT;",
    )

    # Discovery is sorted by filename.
    versions = [m.version for m in discover_migrations(migrations_dir)]
    assert versions == ["0001_a", "0002_b", "0003_c"]

    applied = await run_migrations(conn, migrations_dir)

    # 0002 depends on the table from 0001; success proves ordering held.
    assert applied == ["0001_a", "0002_b", "0003_c"]
    assert await _applied(conn) == ["0001_a", "0002_b", "0003_c"]
    col = await conn.fetchval(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'name'
        """
    )
    assert col == "name"
