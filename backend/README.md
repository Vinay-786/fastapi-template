# Backend

FastAPI service backed by PostgreSQL 18, using raw `asyncpg` (no ORM) with a
hand-rolled, forward-only SQL migration runner.

## Database migrations

Schema changes are managed by a small custom migration runner. There is **no
ORM and no migration framework** (no SQLAlchemy/Alembic) — just plain `*.sql`
files and raw `asyncpg`.

### Layout

```
backend/
├── migrations/                 # ordered SQL migration files
│   └── 0001_create_users.sql
└── src/backend/
    ├── migrations.py           # the migration runner
    └── database.py             # pool + lifespan; runs migrations on startup
```

### How it works

Migrations run automatically on application startup. When the connection pool
is created in `Database.connect()`, a single connection is used to run the
migration process:

1. **Acquire an advisory lock.** A session-level Postgres advisory lock
   (`pg_advisory_lock`) with a fixed application key is taken so that if
   multiple application instances start at once, only one runs migrations; the
   others wait, then find nothing to do.
2. **Ensure the ledger exists.** A `schema_migrations` table is created if
   absent:

   | column       | type          | notes                    |
   | ------------ | ------------- | ------------------------ |
   | `version`    | `TEXT`        | PRIMARY KEY              |
   | `applied_at` | `TIMESTAMPTZ` | `DEFAULT now()`          |

3. **Discover migrations.** All `migrations/*.sql` files are found and sorted
   by filename. Each file's `version` is its filename stem
   (e.g. `0001_create_users`).
4. **Determine pending work.** Versions already present in `schema_migrations`
   are skipped.
5. **Apply pending migrations in order.** Each pending migration runs inside
   its own transaction:
   - the SQL in the file is executed, then
   - a row is inserted into `schema_migrations`.

   Because both happen in the **same transaction**, a failure rolls back the
   entire migration and the version is **not** recorded.
6. **Release the advisory lock**, even if a migration failed.

### Guarantees

The runner is idempotent:

- **Fresh database** → all migrations are applied in order.
- **Already up to date** → nothing is applied (no-op).
- **New migration added** → only the new file is applied.
- **Concurrent instances** → the advisory lock ensures only one runs
  migrations; the rest see no pending work.
- **Failed migration** → rolled back atomically and not recorded, so it is
  retried on the next startup once fixed.

### Rules (forward-only)

Migrations are **forward-only**. There are no down/rollback migrations.

- **Never edit or delete an already-applied migration file.** Once a version is
  recorded in `schema_migrations` it will not run again, so edits to that file
  have no effect on existing databases and will cause drift.
- **To change the schema, add a new file** with the next version number.

### Adding a new migration

1. Create a new file in `backend/migrations/` using the next zero-padded
   number and a short description:

   ```
   migrations/0002_add_email_index.sql
   migrations/0003_add_user_status.sql
   ```

2. Write the change as raw SQL. Prefer idempotent DDL where practical
   (e.g. `CREATE INDEX IF NOT EXISTS ...`), though each migration only runs
   once regardless.

   ```sql
   -- 0002_add_email_index.sql
   CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);
   ```

3. Restart the application. The new migration is detected and applied
   automatically; existing migrations are skipped.

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

The migration runner has tests covering fresh apply, no-op re-runs, incremental
application, transactional rollback of a failed migration, and version-ordered
execution. They require a running Postgres (from the repo root: `docker compose
up -d db`).

```bash
uv run pytest
```
