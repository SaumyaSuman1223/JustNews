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

    gnews_api_key: str | None = None
    ingest_max_gnews_calls_per_day: int = 100

    # --- dedup thresholds (ADR: three layers) ---
    dedup_simhash_max_distance: int = 3
    dedup_embedding_min_cosine: float = 0.86
    dedup_window_hours: int = 72

    article_retention_days: int = 90

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
