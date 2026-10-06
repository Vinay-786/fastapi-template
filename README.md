# fastapi-template

Full-stack template: FastAPI + raw `asyncpg` backend, React + Vite frontend
(TanStack Router/Query), PostgreSQL 18, orchestrated with Docker Compose.

See [`Agent.md`](./Agent.md) for the full project structure and conventions,
and the per-service docs in [`backend/README.md`](./backend/README.md) and
[`frontend/README.md`](./frontend/README.md).

## Toolchain

- **Backend:** Python 3.13 (`backend/.python-version`), managed with `uv`.
- **Frontend:** Node 22 (`frontend/.nvmrc`), managed with `npm`. Run
  `nvm use` in `frontend/` to match the pinned version.
- **Database:** PostgreSQL 18.

## Prerequisites

Install these tools before setting up the project:

**[uv](https://docs.astral.sh/uv/)** — Python package/dependency manager (backend):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**[nvm](https://github.com/nvm-sh/nvm)** — Node version manager (frontend):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash
```

**Docker** — for running the stack via `docker compose`. On macOS you can use
[Colima](https://github.com/abiosoft/colima) as the Docker runtime (install
via [Homebrew](https://brew.sh/), then start it):

```bash
brew install colima docker docker-compose
colima start
```

## Quick start

```bash
# Full stack — frontend on http://localhost:8080, API proxied at /api
make up

# ...or run pieces locally
make db-up          # just Postgres
make backend-dev    # FastAPI with reload (in another shell)
make frontend-dev   # Vite dev server (in another shell)
```

## Makefile

A root `Makefile` provides handy commands for development, database
inspection, and discovery. Run `make` (or `make help`) to list everything:

```bash
make help
```

### Stack lifecycle

| Command      | Description                                        |
| ------------ | -------------------------------------------------- |
| `make up`    | Build and start the full stack (frontend on :8080) |
| `make down`  | Stop and remove the stack (keeps the db volume)    |
| `make db-up` | Start only Postgres (for local backend dev)        |
| `make logs`  | Tail logs for all services                         |
| `make ps`    | Show service status                                |

### Migrations

The backend uses Alembic (no ORM — revisions are hand-written raw SQL via
`op.execute`). Migrations also apply automatically on app startup. These
targets help inspect and manage them (all need `make db-up` first, except
`new-migration`):

| Command                          | Description                                          |
| -------------------------------- | ---------------------------------------------------- |
| `make migrate-status`            | Show current revision and history                    |
| `make migrate`                   | Apply pending migrations (`alembic upgrade head`)    |
| `make new-migration name=<desc>` | Scaffold a new revision (no `--autogenerate`)        |
| `make migrate-downgrade`         | Revert the last revision (dev only)                  |

Example:

```bash
make new-migration name=add_user_status
# creates backend/alembic/versions/<rev>_add_user_status.py
make migrate-status
```

### Backend

| Command                | Description                                  |
| ---------------------- | -------------------------------------------- |
| `make backend-install` | Install backend deps (`uv sync`)             |
| `make backend-dev`     | Run FastAPI with reload (needs `make db-up`) |
| `make backend-test`    | Run pytest (needs Postgres running)          |
| `make backend-test-unit` | Run mocked unit tests (no DB needed)       |
| `make backend-lint`    | Lint backend (`ruff check` + format check)   |
| `make backend-shell`   | Python REPL with the backend importable      |

### Frontend

| Command                 | Description                        |
| ----------------------- | ---------------------------------- |
| `make frontend-install` | Install frontend deps (`npm ci`)   |
| `make frontend-dev`     | Vite dev server (proxies `/api`)   |
| `make frontend-build`   | Type-check and build               |
| `make frontend-lint`    | Lint with oxlint                   |

### Database inspection

| Command          | Description                              |
| ---------------- | ---------------------------------------- |
| `make db-shell`  | Interactive `psql` shell in the db container |
| `make db-tables` | List tables                              |
| `make db-users`  | Show rows in the `users` table           |

### Discovery (handy for agents)

| Command       | Description                                        |
| ------------- | -------------------------------------------------- |
| `make tree`   | Print the source tree (git-ignored files excluded) |
| `make routes` | List backend HTTP routes                           |
| `make info`   | Show pinned versions and local toolchain           |

### Overrides

DB credentials default to the values in `backend/.env.example` and can be
overridden per invocation:

```bash
make db-shell POSTGRES_DB=mydb POSTGRES_USER=admin
```
