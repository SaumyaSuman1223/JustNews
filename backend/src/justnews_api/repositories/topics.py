from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, Topic, TopicLabel


async def list_top_level_topics(session: AsyncSession) -> list[Topic]:
    result = await session.execute(
        select(Topic).where(Topic.active.is_(True), Topic.level == 1).order_by(Topic.id)
    )
    # Topic.labels is lazy="selectin", so this is one query, not N+1.
    return list(result.scalars().unique().all())


async def get_topic(session: AsyncSession, topic_id: str) -> Topic | None:
    return await session.get(Topic, topic_id)


async def list_children(session: AsyncSession, parent_id: str | None) -> list[Topic]:
    """`parent_id=None` is the top-level browse - the same 17 concepts
    `list_top_level_topics` returns, by a different route. A real
    `parent_id` returns nothing today: only level 1 is loaded (see
    `scripts/load_iptc_taxonomy.py`, which does not exist yet). Written
    correctly anyway rather than left unwritten - the admin taxonomy
    browser's drill-down plumbing should not need revisiting the day that
    loader does.
    """
    if parent_id is None:
        return await list_top_level_topics(session)
    result = await session.execute(
        select(Topic).where(Topic.active.is_(True), Topic.parent_id == parent_id).order_by(Topic.id)
    )
    return list(result.scalars().unique().all())


async def search_topics(
    session: AsyncSession, *, query: str, language: str, limit: int
) -> list[Topic]:
    pattern = f"%{query}%"
    result = await session.execute(
        select(Topic)
        .join(TopicLabel, TopicLabel.topic_id == Topic.id)
        .where(
            Topic.active.is_(True),
            TopicLabel.language == language,
            TopicLabel.label.ilike(pattern),
        )
        .order_by(Topic.id)
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def count_articles_by_topic(session: AsyncSession, topic_ids: list[str]) -> dict[str, int]:
    """Primary-tag counts only, matching how the reading-profile's own
    topic breakdown counts (repositories.interactions.reading_mix) - an
    article's non-primary topics should not inflate a count it is not
    really filed under."""
    if not topic_ids:
        return {}
    result = await session.execute(
        select(ArticleTopic.topic_id, func.count(func.distinct(ArticleTopic.article_id)))
        .where(ArticleTopic.topic_id.in_(topic_ids), ArticleTopic.is_primary.is_(True))
        .group_by(ArticleTopic.topic_id)
    )
    return dict(result.tuples().all())
