---
name: fastapi-patterns
description: FastAPI best practices for THIS project — raw asyncpg (no ORM), Pydantic v2 schemas, connection-pool dependency injection, async handlers, transactional service methods, and testing with pytest + httpx. No SQLAlchemy or Alembic. Use when building or reviewing FastAPI code here.
metadata:
  origin: ECC (adapted for this project — raw asyncpg, no SQLAlchemy)
---

# FastAPI Patterns

FastAPI development conventions for this repository.

**Stack note:** this project uses **FastAPI + raw `asyncpg`** with a
hand-rolled forward-only SQL migration runner. There is **no ORM
(no SQLAlchemy) and no migration framework (no Alembic)**. Do not introduce
them — schema changes are plain `*.sql` files in `backend/migrations/`. See
`backend/README.md` and `Agent.md`.

## Project Structure

The actual layout (no `models/` ORM package, no `schemas/` split — Pydantic
models live in `models.py`):

```text
backend/
|-- migrations/            # ordered forward-only *.sql files
`-- src/backend/
    |-- app.py             # FastAPI app, lifespan, routes
    |-- config.py          # env-based settings (os.environ)
    |-- database.py        # asyncpg pool + connection context manager
    |-- migrations.py      # migration runner (advisory lock + ledger)
    |-- models.py          # Pydantic request/response models
    `-- __init__.py        # dev-server entrypoint (main)
```

For a larger app you may add `routers/` and `services/` packages; keep route
handlers thin and push data access into service functions/classes.

---

## App and Lifespan

The lifespan opens the asyncpg pool (which runs pending migrations) on startup
and closes it on shutdown. Do **not** create tables here via an ORM — the
migration runner owns the schema.

```python
# src/backend/app.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .database import db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Opens the pool and applies pending migrations, then serves.
    await db.connect()
    try:
        yield
    finally:
        await db.disconnect()


_settings = get_settings()

app = FastAPI(
    title="Backend",
    lifespan=lifespan,
    debug=_settings.debug,
    # Interactive docs are exposed only in debug mode.
    docs_url="/docs" if _settings.debug else None,
    redoc_url="/redoc" if _settings.debug else None,
    openapi_url="/openapi.json" if _settings.debug else None,
)
```

If you add CORS or other middleware, do it here with
`app.add_middleware(...)`. (Currently the frontend reaches the API via an nginx
`/api` reverse proxy, so CORS is not configured.)

---

## Configuration

Settings are read from environment variables (a local `.env` is loaded via
`python-dotenv`). This project does **not** use `pydantic-settings`.

```python
# src/backend/config.py
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


class Settings:
    def __init__(self) -> None:
        self.debug: bool = _env_bool("DEBUG", default=False)
        self.database_url: str = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/backend",
        )
        self.db_pool_min_size: int = int(os.environ.get("DB_POOL_MIN_SIZE", "1"))
        self.db_pool_max_size: int = int(os.environ.get("DB_POOL_MAX_SIZE", "10"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Add new settings as typed attributes on `Settings`, document them in
`.env.example`, and read them via `get_settings()`.

---

## Pydantic Schemas (v2)

Keep separate input (`*Create`/`*Update`) and output (`*Response`) models. Use
`EmailStr` and `Field(...)` constraints so FastAPI validates requests for you
(returning structured `422`s). Note our IDs are `UUID` and timestamps are
`datetime`, matching the DB columns.

```python
# src/backend/models.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class UserResponse(BaseModel):
    # from_attributes lets us validate from a mapping (dict(asyncpg.Record)).
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    created_at: datetime
```

Build a response from an asyncpg row with
`UserResponse.model_validate(dict(row))`.

---

## Database Access (raw asyncpg)

The pool and a connection context manager live in `database.py`. Acquire a
connection per request/operation via `async with db.connection() as conn`.

```python
# src/backend/database.py (shape)
class Database:
    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        async with self.pool.acquire() as conn:
            yield conn

db = Database()
```

Rules:

- **Always use parameterized queries** (`$1, $2, ...`). Never interpolate user
  input into SQL.
- **`SELECT` only the columns you need**, not `SELECT *`.
- **Wrap multi-statement mutations in a transaction** with
  `async with conn.transaction():`.
- **Rely on DB constraints** (e.g. a `UNIQUE` index) rather than race-prone
  application-level pre-checks; catch `asyncpg.UniqueViolationError`.

---

## Dependency Injection (connection per request)

Prefer FastAPI dependencies to hand a connection to handlers, instead of
opening the context manager inline in every route.

```python
# src/backend/dependencies.py
from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends

from .database import db


async def get_conn() -> AsyncIterator[asyncpg.Connection]:
    async with db.connection() as conn:
        yield conn


ConnDep = Annotated[asyncpg.Connection, Depends(get_conn)]
```

---

## Router and Endpoint Design

Always declare a typed `response_model`. Keep handlers thin; translate driver
errors into meaningful HTTP status codes.

```python
# src/backend/routers/users.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from ..dependencies import ConnDep
from ..models import UserCreate, UserResponse
from ..services.user_service import DuplicateUserError, UserService

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, conn: ConnDep) -> UserResponse:
    try:
        return await UserService(conn).create(payload)
    except DuplicateUserError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )


@router.get("", response_model=list[UserResponse])
async def list_users(
    conn: ConnDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserResponse]:
    return await UserService(conn).list(limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, conn: ConnDep) -> UserResponse:
    user = await UserService(conn).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
```

> The current template registers routes directly on `app` in `app.py`. When the
> API grows, split them into `routers/` and `app.include_router(...)`.

---

## Service Layer (raw asyncpg)

Push data access and business rules into a service that takes a connection.
Enforce **deterministic ordering** on paginated queries, and use explicit
transactions for multi-step mutations.

```python
# src/backend/services/user_service.py
from uuid import UUID

import asyncpg

from ..models import UserCreate, UserResponse, UserUpdate


class DuplicateUserError(Exception):
    """Raised when a unique user field conflicts with an existing row."""


class UserService:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn

    async def create(self, payload: UserCreate) -> UserResponse:
        try:
            row = await self.conn.fetchrow(
                """
                INSERT INTO users (email, full_name)
                VALUES ($1, $2)
                RETURNING id, email, full_name, created_at
                """,
                payload.email,
                payload.full_name,
            )
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateUserError from exc
        return UserResponse.model_validate(dict(row))

    async def get(self, user_id: UUID) -> UserResponse | None:
        row = await self.conn.fetchrow(
            "SELECT id, email, full_name, created_at FROM users WHERE id = $1",
            user_id,
        )
        return UserResponse.model_validate(dict(row)) if row else None

    async def list(self, limit: int = 20, offset: int = 0) -> list[UserResponse]:
        rows = await self.conn.fetch(
            """
            SELECT id, email, full_name, created_at
            FROM users
            ORDER BY created_at DESC, id          -- deterministic ordering
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [UserResponse.model_validate(dict(r)) for r in rows]

    async def update(self, user_id: UUID, payload: UserUpdate) -> UserResponse | None:
        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            return await self.get(user_id)
        # Build a parameterized SET clause safely from a known field allowlist.
        allowed = {"full_name", "email"}
        sets, values = [], []
        for i, (name, value) in enumerate(f for f in fields.items() if f[0] in allowed):
            sets.append(f"{name} = ${i + 1}")
            values.append(value)
        values.append(user_id)
        try:
            async with self.conn.transaction():
                row = await self.conn.fetchrow(
                    f"UPDATE users SET {', '.join(sets)} "
                    f"WHERE id = ${len(values)} "
                    "RETURNING id, email, full_name, created_at",
                    *values,
                )
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateUserError from exc
        return UserResponse.model_validate(dict(row)) if row else None
```

> **Note on DB design:** application-level unique handling requires an
> underlying `UNIQUE` constraint/index (the `users.email` column has one).
> Without it, catching `UniqueViolationError` cannot prevent concurrent races.
> Column allowlists (as above) keep dynamic SQL free of injection.

---

## Authentication (optional — not in this template yet)

The template ships no auth. If you add JWT auth, keep it asyncpg-based and
separate authentication (`401`) from authorization (`403`):

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import get_settings
from .dependencies import ConnDep

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    conn: ConnDep,
):
    settings = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exc
        user_id = UUID(subject)
    except (JWTError, ValueError):
        raise credentials_exc

    row = await conn.fetchrow(
        "SELECT id, email, full_name, created_at FROM users WHERE id = $1", user_id
    )
    if row is None:
        raise credentials_exc
    return UserResponse.model_validate(dict(row))
```

Adding auth means new deps (`python-jose`, `passlib[bcrypt]`) via `uv add`, new
env vars (`SECRET_KEY`, etc.) in `Settings` + `.env.example`, and a migration
for password columns.

---

## Testing with pytest + httpx

The existing suite tests the migration runner directly against a live Postgres
(see `backend/tests/`). For endpoint tests, drive the ASGI app with httpx and
override the connection dependency. There is **no SQLite/aiosqlite** — tests run
against real Postgres (start it with `make db-up`), which matches production
behavior (UUIDs, constraints, `gen_random_uuid()`).

```python
# tests/conftest.py (endpoint testing sketch)
import os

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app import app
from backend.dependencies import get_conn

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/backend"
)


@pytest_asyncio.fixture
async def conn():
    connection = await asyncpg.connect(dsn=DATABASE_URL)
    tx = connection.transaction()
    await tx.start()          # roll back after each test for isolation
    try:
        yield connection
    finally:
        await tx.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(conn: asyncpg.Connection):
    async def override_get_conn():
        yield conn

    app.dependency_overrides[get_conn] = override_get_conn
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
```

```python
# tests/test_users.py
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_and_list_user(client):
    resp = await client.post(
        "/users", json={"email": "a@example.com", "full_name": "Alice"}
    )
    assert resp.status_code == 201

    listed = await client.get("/users")
    assert listed.status_code == 200
    assert any(u["email"] == "a@example.com" for u in listed.json())
```

Adding httpx for tests is a dev dependency: `uv add --dev httpx`.

---

## Anti-Patterns

```python
# Bad: business logic + raw SQL inline in the route handler.
@app.post("/users")
async def create_user(payload: UserCreate):
    async with db.connection() as conn:
        row = await conn.fetchrow("INSERT INTO users ...", payload.email, payload.full_name)
    return dict(row)

# Good: thin route, service handles data access + error translation.
@router.post("", response_model=UserResponse, status_code=201)
async def create_user(payload: UserCreate, conn: ConnDep):
    try:
        return await UserService(conn).create(payload)
    except DuplicateUserError:
        raise HTTPException(status_code=409, detail="Email already exists.")


# Bad: string interpolation -> SQL injection.
row = await conn.fetchrow(f"SELECT * FROM users WHERE email = '{email}'")

# Good: parameterized query, explicit columns.
row = await conn.fetchrow(
    "SELECT id, email, full_name, created_at FROM users WHERE email = $1", email
)
```

---

## Best Practices

- Always declare a typed `response_model` to avoid leaking columns and to
  produce clean OpenAPI schemas.
- Consolidate the connection dependency via a type alias:
  `ConnDep = Annotated[asyncpg.Connection, Depends(get_conn)]`.
- Use parameterized queries everywhere; never interpolate user input into SQL.
- Wrap multi-step mutations in `async with conn.transaction():` and catch
  structural errors (`asyncpg.UniqueViolationError`) in the service layer.
- Enforce deterministic ordering (e.g. `ORDER BY created_at DESC, id`) on all
  `LIMIT/OFFSET` paginated endpoints to avoid skipped/duplicated rows.
- Keep the schema in `migrations/` (forward-only SQL); never create tables from
  the app at runtime and never edit an already-applied migration.
- Separate authentication (`401`) from authorization (`403`) if you add auth.
- Add dependencies with `uv add` (or `uv add --dev`), and document new env vars
  in `.env.example`.
```
