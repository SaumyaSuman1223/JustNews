"""Retention.

Supabase's free tier gives us 500 MB, and an ingestion job that runs every
fifteen minutes forever will fill it. The hot window is 90 days; older
articles are deleted, and clusters left with no articles go with them
(ADR 0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, StoryCluster
from justnews_core.settings import Settings

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PruneResult:
    cutoff: datetime
    articles_deleted: int
    clusters_deleted: int


async def prune(
    session: AsyncSession, settings: Settings, *, now: datetime | None = None
) -> PruneResult:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=settings.article_retention_days)

    articles: CursorResult[Any] = await session.execute(  # type: ignore[assignment]
        delete(Article).where(Article.published_at < cutoff)
    )

    orphan_clusters = select(StoryCluster.id).where(
        ~select(Article.id).where(Article.story_cluster_id == StoryCluster.id).exists()
    )
    clusters: CursorResult[Any] = await session.execute(  # type: ignore[assignment]
        delete(StoryCluster).where(StoryCluster.id.in_(orphan_clusters))
    )

    result = PruneResult(cutoff, articles.rowcount or 0, clusters.rowcount or 0)
    log.info(
        "retention_pruned",
        cutoff=cutoff.isoformat(),
        articles_deleted=result.articles_deleted,
        clusters_deleted=result.clusters_deleted,
    )
    return result


async def database_size_bytes(session: AsyncSession) -> int:
    """Current database size. Alert at 70% of the free-tier 500 MB."""
    return int(await session.scalar(text("SELECT pg_database_size(current_database())")) or 0)


async def article_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Article)) or 0)
