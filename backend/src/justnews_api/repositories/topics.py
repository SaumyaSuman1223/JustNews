from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from justnews_core.models import Article, ArticleTopic, Source, StoryCluster, Topic, TopicLabel


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


@dataclass(frozen=True, slots=True)
class TopicOverview:
    articles: int
    sources: int
    stories: int


async def topic_overview(session: AsyncSession, topic_id: str) -> TopicOverview:
    """My Desk's "Topic Overview" panel - real counts over exactly the set
    `services.content.get_article_page`'s own `topic=` filter would return,
    live articles only."""
    result = await session.execute(
        select(
            func.count(func.distinct(Article.id)),
            func.count(func.distinct(Article.source_id)),
            func.count(func.distinct(Article.story_cluster_id)),
        )
        .select_from(ArticleTopic)
        .join(Article, Article.id == ArticleTopic.article_id)
        .where(ArticleTopic.topic_id == topic_id, Article.removed_at.is_(None))
    )
    articles, sources, stories = result.one()
    return TopicOverview(articles=articles or 0, sources=sources or 0, stories=stories or 0)


async def list_story_clusters_for_topic(
    session: AsyncSession, *, topic_id: str, limit: int
) -> list[StoryCluster]:
    """My Desk's Timeline: every story with at least one live article tagged
    this topic, most recently active first."""
    result = await session.execute(
        select(StoryCluster)
        .join(Article, Article.story_cluster_id == StoryCluster.id)
        .join(ArticleTopic, ArticleTopic.article_id == Article.id)
        .where(ArticleTopic.topic_id == topic_id, Article.removed_at.is_(None))
        .group_by(StoryCluster.id)
        .order_by(StoryCluster.last_seen_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def related_topic_ids(
    session: AsyncSession, topic_id: str, *, limit: int
) -> list[tuple[str, int]]:
    """Topics that most often appear on the same article as `topic_id` -
    "related" as a real co-occurrence count, not a taxonomy-sibling lookup.

    The IPTC hierarchy loader that would make `parent_id` siblings
    meaningful does not exist yet (see `list_children`'s own note) - every
    loaded topic sits at level 1, so a sibling query would return nothing.
    Co-occurrence needs no taxonomy depth at all and is arguably closer to
    what "related" means for a reader anyway.
    """
    other = aliased(ArticleTopic)
    result = await session.execute(
        select(other.topic_id, func.count(func.distinct(other.article_id)))
        .join(ArticleTopic, ArticleTopic.article_id == other.article_id)
        .where(ArticleTopic.topic_id == topic_id, other.topic_id != topic_id)
        .group_by(other.topic_id)
        .order_by(func.count(func.distinct(other.article_id)).desc())
        .limit(limit)
    )
    return list(result.tuples().all())


async def article_source_roles_for_topic(
    session: AsyncSession, topic_id: str, *, limit_clusters: int = 20
) -> list[tuple[str | None, int, str, str, str]]:
    """One row per live article tagged this topic, carrying its publisher's
    role - the raw material `services.perspectives.group_by_role` groups.

    Scoped to the topic's most recently active story clusters (the same
    "recent clusters" `list_story_clusters_for_topic` already serves the
    Timeline with) rather than the topic's entire history - a topic followed
    for months should show today's perspectives, not an average of all time.
    """
    recent_clusters = (
        select(StoryCluster.id)
        .join(Article, Article.story_cluster_id == StoryCluster.id)
        .join(ArticleTopic, ArticleTopic.article_id == Article.id)
        .where(ArticleTopic.topic_id == topic_id, Article.removed_at.is_(None))
        .group_by(StoryCluster.id)
        .order_by(StoryCluster.last_seen_at.desc())
        .limit(limit_clusters)
    )
    result = await session.execute(
        select(Source.source_role, Source.id, Source.slug, Source.name, Source.homepage_url)
        .select_from(Article)
        .join(Source, Source.id == Article.source_id)
        .join(ArticleTopic, ArticleTopic.article_id == Article.id)
        .where(
            ArticleTopic.topic_id == topic_id,
            Article.removed_at.is_(None),
            Article.story_cluster_id.in_(recent_clusters),
        )
    )
    return list(result.tuples().all())
