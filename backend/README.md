# Backend

FastAPI service backed by PostgreSQL 18, using raw `asyncpg` (no ORM) with
Alembic as the migration engine (hand-written raw-SQL revisions, no model
metadata, no `--autogenerate`).

## Database migrations

Schema changes are managed by Alembic. There is **no ORM** — revisions
contain hand-written SQL executed via `op.execute(sa.text(...))`, and the
application itself keeps using raw `asyncpg`. Alembic runs on a short-lived
synchronous SQLAlchemy engine (psycopg v3) only for migrations.

### Layout

```
backend/
├── alembic.ini                   # Alembic config (URL is overridden from DATABASE_URL)
├── alembic/
│   ├── env.py                    # resolves DATABASE_URL -> sync psycopg URL; no metadata
│   ├── script.py.mako            # revision template
│   └── versions/
│       └── 0001_create_users.py  # creates the users table
└── src/backend/
    ├── config.py                 # Settings + to_sync_url() helper
    └── database.py               # pool + lifespan; runs `upgrade head` on startup
```

### How it works

A single `DATABASE_URL` env var (plain `postgresql://`, for asyncpg) is
shared. `to_sync_url()` in `config.py` converts it to
`postgresql+psycopg://` for the migration engine, so no second env var is
needed.

Migrations run automatically on application startup. When the connection pool
is created in `Database.connect()`, `_migrate()` runs `alembic upgrade head`
in a worker thread (`asyncio.to_thread`, since Alembic is synchronous):

1. Resolve `alembic.ini` next to the backend root and point
   `script_location` at `alembic/` with an absolute path (so startup works
   regardless of the process working directory).
2. Override `sqlalchemy.url` with the sync URL derived from `DATABASE_URL`.
3. Run `upgrade head`. Alembic tracks state in its standard
   `alembic_version` table.

The same revisions can be applied from the CLI (see `make migrate`); both
paths converge on `upgrade head`.

### Guarantees

- **Fresh database** → all revisions apply in order.
- **Already up to date** → upgrade is a no-op.
- **Concurrent instances** → only standard Alembic behavior applies; for the
  containerized startup path, upgrades are quick DDL batches. (The previous
  hand-rolled runner used a Postgres advisory lock; Alembic relies on its
  version table + transactional DDL instead.)
- **Failed migration** → the revision's transaction rolls back and the
  version is not recorded, so it is retried on the next startup/upgrade once
  fixed.

### Rules

- **Never edit an already-applied revision.** Once a version is recorded in
  `alembic_version` it will not run again — add a new revision instead.
- **No `--autogenerate`.** There are no ORM models for Alembic to compare
  against (`target_metadata is None`). Write the DDL yourself with
  `op.execute(sa.text(...))` and keep `downgrade()` in sync.
- Keep `downgrade()` honest for local dev; production roll-forward only.

### Adding a new migration

1. Scaffold a revision from the repository root:

   ```bash
   make new-migration name=add_user_status
   # creates backend/alembic/versions/<rev>_add_user_status.py
   ```

   (This runs `alembic revision -m <name>` — never with `--autogenerate`.)

2. Fill in `upgrade()` (and `downgrade()`) with raw SQL:

   ```python
   def upgrade() -> None:
       op.execute(sa.text("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"))

   def downgrade() -> None:
       op.execute(sa.text("ALTER TABLE users DROP COLUMN status"))
   ```

3. Apply it:

   ```bash
   make migrate          # alembic upgrade head (needs make db-up first)
   make migrate-status   # alembic current + history
   ```

   Restarting the application also applies pending revisions automatically
   on startup.

### Migrating from the old hand-rolled runner

Before this change the template used plain `*.sql` files in
`backend/migrations/` with a `schema_migrations` ledger. That runner and
directory are gone. The initial Alembic revision (`0001`) recreates the same
`users` schema from scratch, so **fresh databases just work**.

Existing databases that already have a `schema_migrations` table need a
one-time cutover: back up, `DROP TABLE schema_migrations` (or archive it),
then either let the app startup upgrade apply `0001` onto an empty schema,
or — if the `users` table already exists — run
`alembic stamp 0001` against that database to mark it current without
re-running DDL. Then verify with `make migrate-status`.

## Running locally

Start Postgres from the repository root (the `db` service in the root
`docker-compose.yml`):

```bash
docker compose up -d db
```

Run the app (migrations apply on startup):

```bash
cp .env.example .env
uv run uvicorn backend.app:app --reload
```

## Configuration

Settings are read from environment variables (a local `.env` is loaded
automatically; see `.env.example`).

| Variable            | Default                | Description                                             |
| ------------------- | ---------------------- | ------------------------------------------------------- |
| `DEBUG`             | `false`                | Enables FastAPI debug, auto-reload, and the API docs (`/docs`, `/redoc`). Keep `false` in production. Truthy values: `1`/`true`/`yes`/`on`. |
| `DATABASE_URL`      | local dev DSN          | asyncpg connection string (plain `postgresql://`).      |
| `DB_POOL_MIN_SIZE`  | `1`                    | Minimum asyncpg pool size.                              |
| `DB_POOL_MAX_SIZE`  | `10`                   | Maximum asyncpg pool size.                              |

When `DEBUG=false` the interactive docs endpoints (`/docs`, `/redoc`,
`/openapi.json`) are disabled.

## Tests

Two tiers, split by the `db` pytest marker (see `pyproject.toml`):

- **Unit (mocked, no DB)** — `tests/test_api_unit.py` (endpoint tests with a
  monkeypatched `db.connection` yielding fake connections) and
  `tests/test_config_unit.py` (config/URL/model tests), plus the pure
  `to_sync_url` / single-head checks in `test_alembic_migrations.py`. These
  are what the `prod` CI workflow runs:

  ```bash
  uv run pytest -m "not db"   # or: make backend-test-unit
  ```

- **Integration (needs Postgres)** — Alembic upgrade/downgrade and startup
  migration tests marked `@pytest.mark.db` (from the repo root:
  `docker compose up -d db`):

  ```bash
  uv run pytest   # or: make backend-test (needs make db-up first)
  ```

## Lint

```bash
uv run ruff check .                          # or: make backend-lint
uv run ruff format --check src tests alembic
```
