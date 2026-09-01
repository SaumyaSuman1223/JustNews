# syntax=docker/dockerfile:1
#
# Layer order is chosen so that a source edit - the thing that happens a
# hundred times a day - invalidates only the last two layers. Dependency
# resolution, the slow part, is cached against the lockfile alone.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# --- dependencies -------------------------------------------------------
FROM base AS deps
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY apps/api/pyproject.toml apps/api/
COPY apps/ingestion/pyproject.toml apps/ingestion/
COPY testing/pyproject.toml testing/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# --- runtime ------------------------------------------------------------
FROM base AS runtime
COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/ingestion/ apps/ingestion/
COPY testing/ testing/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Never run as root, even in a container that "only" serves HTTP.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
# Render injects $PORT and it is not always 8000.
CMD ["sh", "-c", "uvicorn justnews_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
