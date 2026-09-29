# ---- Builder: resolve and install dependencies with uv ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# uv configuration for reproducible, container-friendly installs.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install only third-party dependencies first (cached unless lockfile changes).
# --no-install-project keeps our own package out of this layer so source edits
# don't bust the dependency cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- Runtime ----
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Run as a non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app app

# Bring in the pre-built virtual environment (dependencies only).
COPY --from=builder /app/.venv /app/.venv

# Application source and migrations. The migration runner resolves its SQL
# directory as parents[2] of src/backend/migrations.py -> /app/migrations, so
# this layout must be preserved.
COPY src ./src
COPY migrations ./migrations

USER app

EXPOSE 8000

# Migrations run automatically on startup (in app lifespan) before serving.
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
