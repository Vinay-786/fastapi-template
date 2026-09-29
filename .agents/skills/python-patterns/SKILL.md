---
name: python-patterns
description: Pythonic idioms, PEP 8 standards, type hints, and best practices for robust, maintainable Python. Tailored to this project — Python 3.13, managed with uv. Use when writing or reviewing backend Python code and idiomatic structure, typing, or PEP 8 is in question.
metadata:
  origin: ECC (adapted for this project — Python 3.13, uv)
---

# Python Development Patterns

Idiomatic Python patterns for this repository's backend.

**Stack note:** the backend targets **Python 3.13** (`backend/.python-version`,
`requires-python = ">=3.13"`) and is managed with **`uv`** (not `pip`). Use
modern built-in generics (`list[str]`, `dict[str, int]`, `X | None`) — never the
legacy `typing.List`/`Dict`/`Optional` forms. See also
`.agents/skills/fastapi-patterns/SKILL.md` (web layer) and
`.agents/skills/coding-standards/SKILL.md` (cross-cutting conventions).

## When to Activate

- Writing new Python code
- Reviewing Python code
- Refactoring existing Python code
- Designing Python modules

## Core Principles

### 1. Readability Counts

```python
# Good: Clear and readable
def get_active_users(users: list[User]) -> list[User]:
    """Return only active users from the provided list."""
    return [user for user in users if user.is_active]


# Bad: Clever but confusing
def get_active_users(u):
    return [x for x in u if x.a]
```

### 2. Explicit is Better Than Implicit

```python
# Good: Explicit configuration
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Bad: Hidden side effects
import some_module
some_module.setup()  # What does this do?
```

### 3. EAFP - Easier to Ask Forgiveness Than Permission

```python
# Good: EAFP style
def get_value(mapping: dict, key: str, default: object = None) -> object:
    try:
        return mapping[key]
    except KeyError:
        return default

# Bad: LBYL (Look Before You Leap) style
def get_value(mapping: dict, key: str, default: object = None) -> object:
    if key in mapping:
        return mapping[key]
    return default
```

This project already uses EAFP for DB writes — it inserts and catches
`asyncpg.UniqueViolationError` rather than pre-checking for duplicates (a
race-prone LBYL pattern). See `create_user` in `app.py`.

## Type Hints

Python 3.13 — always use built-in generics and union syntax.

```python
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}


def first(items: list[str]) -> str | None:
    """Return the first item, or None if the list is empty."""
    return items[0] if items else None
```

### Type Aliases and TypeVar

```python
from typing import TypeVar

# Type alias for a complex/recurring type
type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

T = TypeVar("T")


def first_of(items: list[T]) -> T | None:
    return items[0] if items else None
```

> Python 3.12+ supports the `type X = ...` alias statement and the newer
> `def f[T](...)` generic syntax; either is fine on 3.13.

### Protocol-Based Duck Typing

```python
from typing import Protocol


class Renderable(Protocol):
    def render(self) -> str: ...


def render_all(items: list[Renderable]) -> str:
    return "\n".join(item.render() for item in items)
```

## Error Handling Patterns

### Specific Exception Handling

```python
# Good: Catch specific exceptions
def load_config(path: str) -> Config:
    try:
        with open(path) as f:
            return Config.from_json(f.read())
    except FileNotFoundError as e:
        raise ConfigError(f"Config file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config: {path}") from e

# Bad: Bare except with silent failure
def load_config(path: str):
    try:
        ...
    except:
        return None
```

### Exception Chaining

```python
def process_data(data: str) -> Result:
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        # `from e` preserves the original traceback.
        raise ValueError(f"Failed to parse data: {data}") from e
```

This is exactly how the backend translates driver errors: it re-raises with
`from exc` (e.g. `asyncpg.UniqueViolationError` → `HTTPException` /
`DuplicateUserError`).

### Custom Exception Hierarchy

```python
class AppError(Exception):
    """Base exception for all application errors."""


class ValidationError(AppError):
    """Raised when input validation fails."""


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""
```

## Context Managers

### Resource Management

```python
# Good: context manager
def process_file(path: str) -> str:
    with open(path) as f:
        return f.read()
```

### Custom Context Managers

```python
from contextlib import asynccontextmanager, contextmanager


@contextmanager
def timer(name: str):
    start = time.perf_counter()
    yield
    print(f"{name} took {time.perf_counter() - start:.4f}s")
```

The project uses `@asynccontextmanager` for both the FastAPI `lifespan` and the
pool's `connection()` accessor (`database.py`). Prefer this pattern for
acquiring/releasing async resources:

```python
@asynccontextmanager
async def connection(self) -> AsyncIterator[asyncpg.Connection]:
    async with self.pool.acquire() as conn:
        yield conn
```

## Comprehensions and Generators

### List Comprehensions

```python
# Good: simple transformation
names = [user.name for user in users if user.is_active]

# Also idiomatic here: building response models from DB rows
return [UserResponse.model_validate(dict(row)) for row in rows]

# Too complex -> use an explicit function/loop instead
```

### Generator Expressions

```python
# Good: lazy, no large intermediate list
total = sum(x * x for x in range(1_000_000))

# Bad: builds a throwaway list first
total = sum([x * x for x in range(1_000_000)])
```

### Generator Functions

```python
from collections.abc import Iterator


def read_large_file(path: str) -> Iterator[str]:
    with open(path) as f:
        for line in f:
            yield line.strip()
```

> Prefer importing `Iterator`, `Iterable`, `AsyncIterator`, etc. from
> `collections.abc` (not `typing`) on modern Python.

## Data Classes and Named Tuples

For API request/response shapes this project uses **Pydantic** models (see
`models.py` and the fastapi-patterns skill). Use `@dataclass` for internal,
non-serialized data containers.

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Migration:
    """Internal value object (cf. migrations.py)."""
    version: str
    path: str


@dataclass
class User:
    email: str
    age: int

    def __post_init__(self) -> None:
        if "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")
        if not 0 <= self.age <= 150:
            raise ValueError(f"Invalid age: {self.age}")
```

Named tuples suit small immutable records:

```python
from typing import NamedTuple


class Point(NamedTuple):
    x: float
    y: float

    def distance(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
```

## Decorators

```python
import functools
import time
from collections.abc import Callable


def timer(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter() - start:.4f}s")
        return result
    return wrapper
```

Parameterized decorator:

```python
def repeat(times: int):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return [func(*args, **kwargs) for _ in range(times)]
        return wrapper
    return decorator
```

`functools.lru_cache` is used in this project for the settings singleton
(`get_settings`); remember it's process-wide (clear with `.cache_clear()` in
tests if you drive it through changing env vars).

## Concurrency Patterns

This is an async (asyncio) backend. Prefer `async`/`await` and
`asyncio.gather` for concurrent I/O.

```python
import asyncio


async def fetch_all(fetchers: list[Callable]) -> list[object]:
    return await asyncio.gather(*(f() for f in fetchers), return_exceptions=True)
```

- **I/O-bound, async libs (asyncpg, httpx):** `await` + `asyncio.gather`.
- **CPU-bound work:** offload to a process pool
  (`concurrent.futures.ProcessPoolExecutor`) so you don't block the event loop.
- **Never** make blocking/synchronous calls inside an async request handler.

## Package Organization

### This project's layout

```
backend/
├── migrations/            # forward-only *.sql
└── src/backend/
    ├── __init__.py        # exports app + main() entrypoint
    ├── app.py
    ├── config.py
    ├── database.py
    ├── migrations.py
    └── models.py
tests/
├── conftest.py
└── test_migrations.py
pyproject.toml
```

### Import Conventions

```python
# Order: stdlib, third-party, local — separated by blank lines.
import os
from pathlib import Path

import asyncpg
from fastapi import FastAPI

from .config import get_settings
from .models import UserResponse
```

Use relative imports within the `backend` package (as the code already does),
and `from __future__ import annotations` at the top of modules for cheap,
forward-compatible annotations.

### `__init__.py` Exports

```python
# src/backend/__init__.py
from .app import app

__all__ = ["app", "main"]
```

## Memory and Performance

### `__slots__` for hot, many-instance classes

```python
class Point:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
```

### Generators for large data

```python
from collections.abc import Iterator


def read_lines(path: str) -> Iterator[str]:
    with open(path) as f:
        for line in f:
            yield line.strip()
```

### Avoid string concatenation in loops

```python
# Bad: O(n²)
result = ""
for item in items:
    result += str(item)

# Good: O(n)
result = "".join(str(item) for item in items)
```

## Python Tooling (uv)

This project uses `uv`. Run tools through it so they use the project venv.

```bash
# Run the test suite (needs Postgres: `make db-up`)
uv run pytest
# ...or via the Makefile
make backend-test

# Add / remove dependencies (never hand-edit pyproject/uv.lock)
uv add <package>
uv add --dev <package>
uv remove <package>

# Sync the environment to the lockfile
uv sync

# If you add linters/formatters/type-checkers, run them through uv, e.g.
uv run ruff check .
uv run mypy src
```

If you introduce Ruff/mypy, add them as a dev dependency (`uv add --dev ruff
mypy`) and configure them in `pyproject.toml`. The existing config already
declares `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` — extend that
file rather than adding parallel config files.

## Quick Reference: Python Idioms

| Idiom | Description |
|-------|-------------|
| EAFP | Easier to Ask Forgiveness than Permission |
| Context managers | Use `with` / `async with` for resource management |
| List comprehensions | For simple transformations |
| Generators | For lazy evaluation and large datasets |
| Type hints | Built-in generics + `X \| None` (3.13) |
| Dataclasses | For internal data containers (Pydantic for I/O) |
| `__slots__` | For memory optimization on hot classes |
| f-strings | For string formatting |
| `pathlib.Path` | For path operations |
| `enumerate` | For index-element pairs in loops |
| `collections.abc` | Import `Iterator`/`Iterable`/`Callable` from here |

## Anti-Patterns to Avoid

```python
# Bad: mutable default argument (shared across calls)
def append_to(item, items=[]):
    items.append(item)
    return items

# Good: sentinel + fresh list
def append_to(item, items: list | None = None) -> list:
    if items is None:
        items = []
    items.append(item)
    return items


# Bad: type() equality      # Good: isinstance()
if type(obj) == list: ...    # if isinstance(obj, list): ...

# Bad: == None               # Good: is None
if value == None: ...        # if value is None: ...

# Bad: wildcard import       # Good: explicit imports
from os.path import *        # from os.path import join, exists

# Bad: bare except swallows everything
try:
    risky()
except:
    pass

# Good: specific exception, logged
try:
    risky()
except SpecificError as e:
    logger.error("Operation failed: %s", e)
```

**Remember**: Python code should be readable, explicit, and follow the principle
of least surprise. When in doubt, prioritize clarity over cleverness.
