# Agent.md

Guidance and structural reference for AI agents working in this repository.

## Overview

A full-stack template:

- **Backend** — FastAPI + raw `asyncpg` (no ORM), with a hand-rolled
  forward-only SQL migration runner. Managed with `uv`.
- **Frontend** — React 19 + Vite, TanStack Router + TanStack Query, served by
  nginx in production.
- **Database** — PostgreSQL 18.
- **Orchestration** — a single root `docker-compose.yml` wires all three
  services together; each app has its own `Dockerfile`.

## Conventions

- **Package managers:** backend uses `uv`; frontend uses `npm` (Node 22, pinned
  in `frontend/.nvmrc`). Do not introduce `pnpm`/`yarn`.
- **Common tasks** are exposed via the root `Makefile` — run `make help` to
  list them (stack lifecycle, migrations, tests, db inspection, discovery).
- **No ORM, no migration framework.** Schema changes are plain `*.sql` files in
  `backend/migrations/`, applied on startup. Migrations are forward-only: never
  edit or delete an applied file — add a new numbered one.
- **API routing:** the frontend fetches origin-relative `/api/...`. In dev the
  Vite proxy forwards it; in production nginx reverse-proxies `/api/` to the
  backend (stripping the `/api` prefix).
- **Secrets:** `.env` files are git-ignored; only `*.env.example` is committed.
- **Debug mode:** the backend reads a `DEBUG` env var (default `false`). It
  enables FastAPI debug, auto-reload, and the interactive docs (`/docs`,
  `/redoc`). Keep it `false` in production; the containerized stack defaults it
  to `false` and it can be overridden with `DEBUG=true docker compose up`.

## Working principles (for agents)

- **Keep the stack simple.** Prefer the tools already in use (FastAPI, raw
  `asyncpg`, React/Vite, plain SQL, Docker Compose, Make). Do not introduce new
  frameworks, ORMs, build tools, or services unless the task genuinely requires
  it — justify any addition and confirm before adding.
- **Discover before assuming.** Check what commands and tooling exist before
  reaching for something new: run `make help` for available tasks, inspect
  `pyproject.toml` / `package.json` scripts, and read config files
  (`docker-compose.yml`, `Dockerfile`, `Makefile`, `vite.config.ts`).
- **Use package managers for dependencies — only.** Add/remove backend deps with
  `uv add` / `uv remove` and frontend deps with `npm install` / `npm uninstall`.
  Never hand-edit `pyproject.toml`/`uv.lock` or `package.json`/`package-lock.json`
  dependency entries by hand, and don't vendor code that belongs in a package.
- **Keep documentation current.** When you add a file, command, env var, or
  convention, update the relevant docs in the same change: this `Agent.md`
  (structure/conventions), the root `README.md` (setup + Makefile), and the
  per-service READMEs. If you add a Make target, ensure it has a `##` help line.
- **New infrastructure services go in Docker Compose.** If a task genuinely
  requires a new backing service (e.g. Redis, RabbitMQ), add it as a service in
  the root `docker-compose.yml` (with a healthcheck and, if needed for local
  dev, a published port), wire its connection settings through env vars +
  `.env.example`, and document it here and in the relevant README.
- **Fresh clone: update dependencies first.** Immediately after cloning — and
  before writing any application code — pull the latest dependencies so you
  start from a current, consistent baseline:

  ```bash
  # Backend (from backend/): resolve + install the latest allowed versions
  cd backend && uv sync --upgrade

  # Frontend (from frontend/): match Node, then update to latest allowed versions
  cd frontend && nvm use && npm update
  ```

  Review the resulting lockfile changes (`uv.lock`, `package-lock.json`) and run
  the build/tests (`make backend-test`, `make frontend-build`) before starting
  feature work.

## Running

```bash
# Full stack (frontend on http://localhost:8080)
docker compose up --build

# Backend only, for local dev
docker compose up -d db
cd backend && cp .env.example .env && uv run uvicorn backend.app:app --reload

# Backend tests (needs the db service running)
cd backend && uv run pytest

# Frontend dev server
cd frontend && npm run dev
```

## Project structure

The trees below reflect only version-controlled files (git-ignored artifacts
such as `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, and `.pytest_cache/`
are omitted).

```
.
├── backend
│   ├── migrations
│   │   └── 0001_create_users.sql
│   ├── src
│   │   └── backend
│   │       ├── __init__.py
│   │       ├── app.py
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── migrations.py
│   │       └── models.py
│   ├── tests
│   │   ├── conftest.py
│   │   └── test_migrations.py
│   ├── .dockerignore
│   ├── .env.example
│   ├── .gitignore
│   ├── .python-version
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── README.md
│   └── uv.lock
├── frontend
│   ├── public
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src
│   │   ├── api
│   │   │   └── users.ts
│   │   ├── assets
│   │   │   ├── hero.png
│   │   │   ├── react.svg
│   │   │   └── vite.svg
│   │   ├── pages
│   │   │   └── HomePage.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── router.tsx
│   ├── .dockerignore
│   ├── .gitignore
│   ├── .nvmrc
│   ├── .oxlintrc.json
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── .gitignore
├── Agent.md
├── docker-compose.yml
├── Makefile
└── README.md

12 directories, 46 files
```

## Key files

### Backend (`backend/`)

- `src/backend/app.py` — FastAPI app, lifespan (opens the pool, runs
  migrations), and the `/users` routes.
- `src/backend/database.py` — asyncpg connection pool + connection
  context manager; invokes the migration runner on startup.
- `src/backend/migrations.py` — forward-only migration runner (advisory lock,
  `schema_migrations` ledger, per-migration transactions).
- `src/backend/models.py` — pydantic `UserCreate` / `UserResponse`.
- `src/backend/config.py` — env-based settings (`DATABASE_URL`, pool sizing).
- `migrations/*.sql` — ordered schema migrations.
- `tests/` — pytest + pytest-asyncio suite for the migration runner (needs a
  running Postgres).

### Frontend (`frontend/`)

- `src/main.tsx` — mounts `QueryClientProvider` + `RouterProvider`.
- `src/router.tsx` — TanStack Router route tree (root + index).
- `src/pages/HomePage.tsx` — home page; fetches the users list via
  TanStack Query.
- `src/api/users.ts` — `User` type and `fetchUsers()` (hits `/api/users`).
- `vite.config.ts` — dev server with `/api` proxy to the backend.
- `nginx.conf` — production reverse proxy for `/api` + SPA fallback.

### Root

- `docker-compose.yml` — `db` (postgres:18), `backend` (FastAPI), `frontend`
  (nginx). The frontend is the single exposed entry point on port `8080`.
