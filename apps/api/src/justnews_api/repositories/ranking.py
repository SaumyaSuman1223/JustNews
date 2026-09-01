"""Signals the Stage 5 heuristic ranker scores candidates on, beyond what
``ArticleRow`` already carries (recency from ``published_at``, source trust
from ``source_trust_score``)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, InteractionEvent


async def topic_ids_by_article(
    session: AsyncSession, article_ids: list[int]
) -> dict[int, list[str]]:
    if not article_ids:
        return {}
    result = await session.execute(
        select(ArticleTopic.article_id, ArticleTopic.topic_id).where(
            ArticleTopic.article_id.in_(article_ids)
        )
    )
    by_article: dict[int, list[str]] = {}
    for article_id, topic_id in result.all():
        by_article.setdefault(article_id, []).append(topic_id)
    return by_article


async def recent_click_counts(
    session: AsyncSession, article_ids: list[int], *, since: datetime
) -> dict[int, int]:
    """Clicks logged against each article since ``since`` - the ranker's
    popularity signal. Weak by design at beta scale (few readers, few
    clicks); it firms up as real traffic accumulates rather than needing to
    change shape later."""
    if not article_ids:
        return {}
    result = await session.execute(
        select(InteractionEvent.article_id, func.count().label("n"))
        .where(
            InteractionEvent.event_type == "click",
            InteractionEvent.created_at >= since,
            InteractionEvent.article_id.in_(article_ids),
        )
        .group_by(InteractionEvent.article_id)
    )
    return {row.article_id: row.n for row in result.all()}


async def seen_article_ids(session: AsyncSession, user_id: UUID, *, since: datetime) -> set[int]:
    """Articles this reader has already clicked into recently - the
    already-seen penalty. Bounded by ``since`` rather than all of history:
    an article read a month ago is not the reason to suppress it forever."""
    result = await session.execute(
        select(InteractionEvent.article_id).where(
            InteractionEvent.user_id == user_id,
            InteractionEvent.event_type == "click",
            InteractionEvent.created_at >= since,
        )
    )
    return set(result.scalars().all())
