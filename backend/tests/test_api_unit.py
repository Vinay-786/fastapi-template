"""Unit tests for the FastAPI user endpoints (no database required).

All DB access goes through ``db.connection()``, so each test monkeypatches
that method to yield a fake connection. Requests run in-process via
``httpx.ASGITransport`` — no live server, no lifespan pool, no network.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import asyncpg
import httpx
import pytest

from backend.app import app
from backend.database import db


def _user_row(email: str = "a@example.com", full_name: str = "Alice") -> dict:
    return {
        "id": uuid4(),
        "email": email,
        "full_name": full_name,
        "created_at": datetime.now(UTC),
    }


def _patch_connection(monkeypatch: pytest.MonkeyPatch, fake_conn) -> None:
    """Monkeypatch ``db.connection`` to yield ``fake_conn``."""

    @asynccontextmanager
    async def _fake_connection():
        yield fake_conn

    # ``db`` is the shared singleton used by the route handlers.
    monkeypatch.setattr(db, "connection", _fake_connection)


def _make_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


class _StubConn:
    """Default stub: fails loudly if a test touches the DB unexpectedly."""

    async def fetchrow(self, *args, **kwargs):
        raise AssertionError("stub not configured for this test")

    async def fetch(self, *args, **kwargs):
        raise AssertionError("stub not configured for this test")


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    """Client with a stub connection (for tests that never reach the DB)."""
    _patch_connection(monkeypatch, _StubConn())
    async with _make_client() as c:
        yield c


async def test_create_user_returns_201(monkeypatch: pytest.MonkeyPatch):
    row = _user_row()

    class _Conn:
        async def fetchrow(self, *args, **kwargs):
            assert kwargs == {} or args  # query + params passed through
            return row

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.post("/users", json={"email": row["email"], "full_name": "Alice"})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == row["email"]
    assert body["id"] == str(row["id"])


async def test_create_user_duplicate_email_returns_409(monkeypatch: pytest.MonkeyPatch):
    class _Conn:
        async def fetchrow(self, *args, **kwargs):
            raise asyncpg.UniqueViolationError("duplicate key value")

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.post("/users", json={"email": "dup@example.com", "full_name": "Dup"})

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_create_user_invalid_email_returns_422(client: httpx.AsyncClient):
    resp = await client.post("/users", json={"email": "not-an-email", "full_name": "Bob"})
    assert resp.status_code == 422


async def test_create_user_missing_full_name_returns_422(client: httpx.AsyncClient):
    resp = await client.post("/users", json={"email": "a@example.com"})
    assert resp.status_code == 422


async def test_list_users_returns_rows(monkeypatch: pytest.MonkeyPatch):
    rows = [_user_row("a@example.com"), _user_row("b@example.com")]

    class _Conn:
        async def fetch(self, *args, **kwargs):
            return rows

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.get("/users")

    assert resp.status_code == 200, resp.text
    assert [r["email"] for r in resp.json()] == ["a@example.com", "b@example.com"]


async def test_list_users_empty(monkeypatch: pytest.MonkeyPatch):
    class _Conn:
        async def fetch(self, *args, **kwargs):
            return []

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.get("/users")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_user_found(monkeypatch: pytest.MonkeyPatch):
    row = _user_row()

    class _Conn:
        async def fetchrow(self, *args, **kwargs):
            return row

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.get(f"/users/{row['id']}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(row["id"])


async def test_get_user_not_found_returns_404(monkeypatch: pytest.MonkeyPatch):
    class _Conn:
        async def fetchrow(self, *args, **kwargs):
            return None

    _patch_connection(monkeypatch, _Conn())
    async with _make_client() as client:
        resp = await client.get(f"/users/{uuid4()}")

    assert resp.status_code == 404


async def test_get_user_invalid_uuid_returns_422(client: httpx.AsyncClient):
    resp = await client.get("/users/not-a-uuid")
    assert resp.status_code == 422
