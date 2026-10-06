"""Unit tests for config + models (no database, no I/O)."""

from __future__ import annotations

from datetime import UTC

import pytest

from backend.config import Settings, _env_bool, to_sync_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+asyncpg://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("sqlite:///local.db", "sqlite:///local.db"),
    ],
)
def test_to_sync_url_variants(raw: str, expected: str):
    assert to_sync_url(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("anything-else", False),
    ],
)
def test_env_bool_parsing(monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool):
    monkeypatch.setenv("FLAG", raw)
    assert _env_bool("FLAG") is expected


def test_env_bool_missing_uses_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FLAG", raising=False)
    assert _env_bool("FLAG") is False
    assert _env_bool("FLAG", default=True) is True


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_POOL_MIN_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_SIZE", raising=False)
    settings = Settings()
    assert settings.debug is False
    assert settings.database_url.startswith("postgresql://")
    assert settings.db_pool_min_size == 1
    assert settings.db_pool_max_size == 10


def test_settings_debug_truthy(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEBUG", "true")
    assert Settings().debug is True


def test_settings_sync_url_derived(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    assert Settings().sync_database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_user_models_round_trip():
    from datetime import datetime
    from uuid import uuid4

    from backend.models import UserCreate, UserResponse

    created = UserCreate(email="a@example.com", full_name="Alice")
    assert created.email == "a@example.com"

    row = {
        "id": uuid4(),
        "email": "a@example.com",
        "full_name": "Alice",
        "created_at": datetime.now(UTC),
    }
    resp = UserResponse.model_validate(dict(row))
    assert resp.email == "a@example.com"
    assert resp.id == row["id"]


def test_user_create_rejects_bad_input():
    from pydantic import ValidationError

    from backend.models import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", full_name="Alice")
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", full_name="")
