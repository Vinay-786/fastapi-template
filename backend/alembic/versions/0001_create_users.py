"""create users table

Revision ID: 0001
Revises: None
Create Date: 2026-10-05

Port of the original forward-only SQL migration
(backend/migrations/0001_create_users.sql) to Alembic. No ORM is involved:
the DDL is executed as raw SQL via op.execute().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email      TEXT NOT NULL UNIQUE,
                full_name  TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS users"))
