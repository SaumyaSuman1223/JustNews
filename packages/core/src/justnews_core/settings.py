"""Process configuration, read once from the environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "staging", "production"]


def _find_env_file() -> Path | None:
    """Locate ``.env`` by walking up from this file to the repo root.

    Commands run from several working directories - ``alembic`` from
    ``apps/api``, the ingestion CLI from anywhere, pytest from the root - and a
    CWD-relative ``.env`` silently resolves to different files depending on
    where you happened to be standing. Walking up finds the same one every time.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
        if (parent / "pnpm-workspace.yaml").is_file():
            break
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Environment = "local"
    log_level: str = "info"

    database_url: PostgresDsn = Field(
        default=PostgresDsn(
            "postgresql+asyncpg://justnews:change_me_locally@localhost:5432/justnews"
        )
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _default_to_asyncpg(cls, value: object) -> object:
        """Supabase's dashboard hands out a bare ``postgresql://`` connection
        string - there is no async driver in it, and no reason every place
        that pastes one in (Render, GitHub Actions secrets, a teammate's
        `.env`) has to remember to add ``+asyncpg`` by hand. ``sync_database_url``
        below depends on this always being present to swap in ``+psycopg``."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value

    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_command_timeout_seconds: float = 10.0

    # --- content pipeline ---
    embedder: Literal["hashing", "sentence-transformers"] = "hashing"
    embedding_dim: int = 384
    # ``halfvec`` halves embedding storage (768 bytes rather than 1536 per
    # article), which is real money against a 500 MB free-tier budget. It needs
    # pgvector >= 0.7; Supabase ships 0.8.x so production always gets it. Some
    # local toolchains bundle an older pgvector, and ``vector`` lets those run
    # the same migrations. The two types are not binary-compatible, so changing
    # this against an existing database means re-embedding the corpus.
    vector_type: Literal["halfvec", "vector"] = "halfvec"
    sentence_transformer_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    ingest_user_agent: str = "JustNewsBot/0.1 (+https://justnews.example/bot)"
    ingest_http_timeout_seconds: float = 15.0
    ingest_per_host_delay_seconds: float = 1.0
    ingest_max_feed_concurrency: int = 8
    ingest_max_entries_per_feed: int = 60
    ingest_snippet_max_chars: int = 300

    # A run must always finish before the next one starts. The cron fires every
    # 15 minutes and the GitHub Actions job is capped at 12 minutes (720s), so
    # a pass that overruns is not slow - it is killed, mid-write, by whichever
    # limit it hits first. The deadline below makes the run stop cleanly and
    # record what it managed instead.
    ingest_run_deadline_seconds: float = 540.0
    # Enrichment is the expensive part: one HTTP fetch per article, throttled
    # per host. It improves articles that a feed left without an image or
    # summary; it is never required. Capped so it can never consume the run.
    ingest_max_enrich_per_run: int = 120
    ingest_max_enrich_concurrency: int = 6

    gnews_api_key: str | None = None
    ingest_max_gnews_calls_per_day: int = 100
    # `run` fires ~96 times/day; reserve_call's per-day cap is the real
    # backstop regardless, but spending only this many calls per pass keeps
    # daily usage comfortably under the cap rather than front-loading it.
    ingest_max_gnews_calls_per_run: int = 1
    # How far back thin_languages looks when counting recent articles per
    # language to decide which ones need a GNews backfill this run.
    gnews_backfill_window_hours: int = 24
    # Seconds of the run deadline set aside exclusively for GNews backfill.
    # Without this, a feed catalog large enough to fill the whole deadline on
    # RSS alone (measured: it does, every run, in steady state) means
    # backfill never gets a turn at all - RSS having first claim on the
    # budget was the intent, RSS having the *entire* budget every single run
    # was not.
    gnews_backfill_reserved_seconds: float = 45.0

    # --- dedup thresholds (ADR: three layers) ---
    dedup_simhash_max_distance: int = 3
    dedup_embedding_min_cosine: float = 0.86
    dedup_window_hours: int = 72

    article_retention_days: int = 90

    # --- auth (Supabase JWT verification via JWKS) ---
    # The API verifies JWTs itself; it never relies on Supabase's own
    # ``auth.uid()`` since browsers never talk to Postgres directly (ADR 0007).
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_seconds: float = 600.0
    auth_http_timeout_seconds: float = 5.0

    # --- rate limiting (Upstash Redis REST API - no persistent connection,
    # which is what makes it viable on a free-tier host that scales to zero
    # or spins down when idle) ---
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None
    rate_limit_requests_per_minute: int = 120

    @property
    def supabase_jwks_url(self) -> str | None:
        if self.supabase_url is None:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_jwt_issuer(self) -> str | None:
        if self.supabase_url is None:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @field_validator("log_level")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()

    @property
    def sync_database_url(self) -> str:
        """Alembic drives migrations synchronously."""
        return str(self.database_url).replace("+asyncpg", "+psycopg")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
