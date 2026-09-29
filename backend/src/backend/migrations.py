"""Forward-only SQL migration runner.

No ORM and no migration framework. Migrations are plain ``*.sql`` files in a
directory, applied in filename order, each inside its own transaction. Applied
versions are recorded in a ``schema_migrations`` ledger table so re-runs are a
no-op. A Postgres advisory lock serializes concurrent runners across instances.

Rules:
  * Forward-only: no down/rollback migrations.
  * Never edit or delete an already-applied migration; add a new file instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import asyncpg

# Arbitrary but fixed application-defined key for pg_advisory_lock. Any two
# runners using the same key contend for the same lock, so only one applies
# migrations at a time.
_MIGRATION_LOCK_KEY = 727_2025_0001

# Default location: backend/migrations (this file lives in
# backend/src/backend/migrations.py).
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

_CREATE_LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


@dataclass(frozen=True)
class Migration:
    """A single migration file on disk."""

    version: str
    path: Path

    def read_sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    """Return all ``*.sql`` migrations sorted by filename/version.

    The ``version`` is the filename stem (e.g. ``0001_create_users``). Zero
    matches returns an empty list rather than raising, so an empty directory is
    a valid (no-op) state.
    """
    if not migrations_dir.is_dir():
        return []

    files = sorted(migrations_dir.glob("*.sql"), key=lambda p: p.name)
    return [Migration(version=p.stem, path=p) for p in files]


async def _ensure_ledger(conn: asyncpg.Connection) -> None:
    await conn.execute(_CREATE_LEDGER_SQL)


async def _applied_versions(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT version FROM schema_migrations")
    return {row["version"] for row in rows}


async def _apply_one(conn: asyncpg.Connection, migration: Migration) -> None:
    """Run a single migration and record it, atomically.

    The DDL and the ledger insert share one transaction: if the SQL fails the
    whole thing rolls back and the version is never recorded.
    """
    sql = migration.read_sql()
    async with conn.transaction():
        await conn.execute(sql)
        await conn.execute(
            "INSERT INTO schema_migrations (version) VALUES ($1)",
            migration.version,
        )


async def run_migrations(
    conn: asyncpg.Connection,
    migrations_dir: Path | None = None,
) -> list[str]:
    """Apply all pending migrations in order on the given connection.

    Uses a session-level advisory lock so concurrent instances cannot run
    migrations at the same time. Returns the list of versions applied during
    this call (empty if the database was already up to date).
    """
    migrations_dir = migrations_dir or DEFAULT_MIGRATIONS_DIR

    # Serialize across instances. Session-level lock is auto-released if the
    # connection drops; we also release explicitly in the finally block.
    await conn.execute("SELECT pg_advisory_lock($1)", _MIGRATION_LOCK_KEY)
    applied: list[str] = []
    try:
        await _ensure_ledger(conn)
        already = await _applied_versions(conn)

        for migration in discover_migrations(migrations_dir):
            if migration.version in already:
                continue
            await _apply_one(conn, migration)
            applied.append(migration.version)
    finally:
        await conn.execute("SELECT pg_advisory_unlock($1)", _MIGRATION_LOCK_KEY)

    return applied
