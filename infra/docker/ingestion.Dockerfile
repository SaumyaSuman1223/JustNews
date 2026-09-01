# syntax=docker/dockerfile:1
#
# Same image shape as the API. Deployed as a Cloud Run *Job*, invoked on a
# schedule by GitHub Actions - a free tier has nowhere to put an always-on
# worker (ADR 0003), and the same cron doubles as the Supabase keep-alive.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM base AS deps
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY apps/api/pyproject.toml apps/api/
COPY apps/ingestion/pyproject.toml apps/ingestion/
COPY testing/pyproject.toml testing/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

FROM base AS runtime
COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/ingestion/ apps/ingestion/
COPY testing/ testing/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

ENTRYPOINT ["justnews-ingest"]
CMD ["run"]
