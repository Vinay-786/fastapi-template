# Agent.md

Guidance and structural reference for AI agents working in this repository.

## Overview

A full-stack template:

- **Backend** — FastAPI + raw `asyncpg` (no ORM), with Alembic as the
  migration engine (hand-written raw-SQL revisions, no model metadata).
  Managed with `uv`.
- **Frontend** — React 19 + Vite, TanStack Router + TanStack Query, served by
  nginx in production.
- **Database** — PostgreSQL 18.
- **Orchestration** — a single root `docker-compose.yml` wires all three
  services together; each app has its own `Dockerfile`.

## Conventions

### Skills

Project skills live in `.agents/skills/<name>/SKILL.md` — the standard
[Agent Skills](https://agentskills.io/specification) location, auto-discovered
by pi and opencode. If your agent doesn't discover them there, mirror/move the
`.agents/skills/` directory to the location it expects (e.g. `.claude/skills/`
for Claude, `.opencode/skills/` for opencode); the `SKILL.md` files themselves
are spec-compliant and portable as-is.

- **Coding standards:** see `.agents/skills/coding-standards/SKILL.md` for
  baseline naming, immutability, error-handling, and code-smell conventions
  (tailored to this React + Vite / FastAPI + asyncpg stack).
- **FastAPI patterns:** see `.agents/skills/fastapi-patterns/SKILL.md` for
  backend structure, Pydantic v2 schemas, connection-pool DI, transactional
  service methods, and testing — all raw-asyncpg (no SQLAlchemy/Alembic).
- **Python patterns:** see `.agents/skills/python-patterns/SKILL.md` for
  idiomatic Python 3.13 (type hints, EAFP, context managers, async), `uv`
  tooling, and anti-patterns to avoid.
- **React patterns:** see `.agents/skills/react-patterns/SKILL.md` for React 19
  in a Vite SPA — hooks discipline, TanStack Query data fetching, forms, state
  location, and composition (no Next.js/RSC).

### General

- **Package managers:** backend uses `uv`; frontend uses `npm` (Node 22, pinned
  in `frontend/.nvmrc`). Do not introduce `pnpm`/`yarn`.
- **Common tasks** are exposed via the root `Makefile` — run `make help` to
  list them (stack lifecycle, migrations, tests, db inspection, discovery).
- **No ORM. Alembic for migrations, raw SQL inside.** Data access is raw
  `asyncpg`; schema changes are Alembic revisions in `backend/alembic/versions/`
  with hand-written `op.execute(sa.text(...))` — no model metadata, no
  `--autogenerate`. Never edit an applied revision — add a new one.
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
├── .agents
│   └── skills
│       ├── coding-standards
│       │   └── SKILL.md
│       ├── fastapi-patterns
│       │   └── SKILL.md
│       ├── python-patterns
│       │   └── SKILL.md
│       └── react-patterns
│           └── SKILL.md
├── backend
│   ├── alembic
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions
│   │       └── 0001_create_users.py
│   ├── alembic.ini
│   ├── src
│   │   └── backend
│   │       ├── __init__.py
│   │       ├── app.py
│   │       ├── config.py
│   │       ├── database.py
│   │       └── models.py
│   ├── tests
│   │   ├── conftest.py
│   │   └── test_alembic_migrations.py
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

18 directories, 50 files
```

## Key files

### Backend (`backend/`)

- `src/backend/app.py` — FastAPI app, lifespan (opens the pool, runs
  migrations), and the `/users` routes.
- `src/backend/database.py` — asyncpg connection pool + connection
  context manager; runs `alembic upgrade head` on startup.
- `src/backend/config.py` — env-based settings (`DATABASE_URL`, pool sizing)
  plus `to_sync_url()` for the Alembic sync URL.
- `src/backend/models.py` — pydantic `UserCreate` / `UserResponse`.
- `alembic/versions/*.py` — ordered schema revisions (raw SQL, no ORM).
- `alembic/env.py` — DB URL from the environment; no model metadata.
- `tests/` — pytest + pytest-asyncio suite for Alembic migrations (needs a
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
