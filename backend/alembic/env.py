"""Alembic environment: synchronous migrations, no ORM.

The application itself uses raw asyncpg (async). Migrations run through
Alembic + SQLAlchemy with the synchronous psycopg driver, on a separate
short-lived engine that is disposed after each run.

There is intentionally NO model metadata here (target_metadata is None):
revisions are hand-written raw SQL via ``op.execute()``. Do not use
``alembic revision --autogenerate`` — create revisions with
``make new-migration name=<description>`` (``alembic revision -m``) and
write the DDL yourself.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make the src-layout backend package importable when Alembic runs with
# backend/ as the working directory.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.config import get_settings, to_sync_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM models: migrations carry their own raw SQL.
target_metadata = None


def get_url() -> str:
    """Resolve the sync SQLAlchemy URL from DATABASE_URL."""
    return to_sync_url(get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
