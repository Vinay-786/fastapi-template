"""FastAPI application: lifespan-managed asyncpg pool and User endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, status

from .config import get_settings
from .database import db
from .models import UserCreate, UserResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the connection pool on startup, close it on shutdown."""
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
    # Interactive API docs are exposed only in debug mode.
    docs_url="/docs" if _settings.debug else None,
    redoc_url="/redoc" if _settings.debug else None,
    openapi_url="/openapi.json" if _settings.debug else None,
)


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(payload: UserCreate) -> UserResponse:
    async with db.connection() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, full_name)
                VALUES ($1, $2)
                RETURNING id, email, full_name, created_at
                """,
                payload.email,
                payload.full_name,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            ) from exc

    return UserResponse.model_validate(dict(row))


@app.get("/users", response_model=list[UserResponse])
async def list_users() -> list[UserResponse]:
    async with db.connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, email, full_name, created_at
            FROM users
            ORDER BY created_at DESC
            """
        )

    return [UserResponse.model_validate(dict(row)) for row in rows]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID) -> UserResponse:
    async with db.connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, full_name, created_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return UserResponse.model_validate(dict(row))
