"""Read-side queries for the admin console: moderation, ops health, and
analytics. Nothing here is reachable except behind ``core.db.get_admin_session``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories.content import ArticleRow
from justnews_core.models import (
    AdminAuditLog,
    Article,
    Feed,
    Impression,
    IngestRun,
    InteractionEvent,
    Source,
)

# --------------------------------------------------------------------------
# Moderation
# --------------------------------------------------------------------------


async def takedown_article(session: AsyncSession, article_id: int, reason: str) -> Article | None:
    article = await session.get(Article, article_id)
    if article is None:
        return None
    article.removed_at = datetime.now(UTC)
    article.removed_reason = reason
    await session.flush()
    return article


async def restore_article(session: AsyncSession, article_id: int) -> Article | None:
    article = await session.get(Article, article_id)
    if article is None:
        return None
    article.removed_at = None
    article.removed_reason = None
    await session.flush()
    return article


async def list_removed_articles(session: AsyncSession, *, limit: int) -> list[ArticleRow]:
    query = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.removed_at.is_not(None))
        .order_by(Article.removed_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


# --------------------------------------------------------------------------
# Ops health
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceHealth:
    id: int
    name: str
    slug: str
    language: str
    active: bool
    feed_count: int
    failing_feed_count: int
    last_success_at: datetime | None
    article_count: int


async def source_health(session: AsyncSession) -> list[SourceHealth]:
    query = (
        select(
            Source.id,
            Source.name,
            Source.slug,
            Source.language,
            Source.active,
            func.count(func.distinct(Feed.id)).label("feed_count"),
            func.count(func.distinct(Feed.id))
            .filter(Feed.consecutive_failures > 0)
            .label("failing_feed_count"),
            func.max(Feed.last_success_at).label("last_success_at"),
            func.count(func.distinct(Article.id)).label("article_count"),
        )
        .outerjoin(Feed, Feed.source_id == Source.id)
        .outerjoin(Article, Article.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.name)
    )
    rows = await session.execute(query)
    return [
        SourceHealth(
            id=row.id,
            name=row.name,
            slug=row.slug,
            language=row.language,
            active=row.active,
            feed_count=row.feed_count,
            failing_feed_count=row.failing_feed_count,
            last_success_at=row.last_success_at,
            article_count=row.article_count,
        )
        for row in rows
    ]


async def recent_ingest_runs(session: AsyncSession, *, limit: int) -> list[IngestRun]:
    query = select(IngestRun).order_by(IngestRun.started_at.desc()).limit(limit)
    return list((await session.execute(query)).scalars().all())


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------


async def active_user_count(session: AsyncSession, since: datetime) -> int:
    """Distinct users with an impression or a logged interaction since
    ``since`` - a UNION rather than two counts added together, since a user
    active in both would otherwise be double-counted."""
    impressed = select(Impression.user_id).where(
        Impression.user_id.is_not(None), Impression.served_at >= since
    )
    interacted = select(InteractionEvent.user_id).where(
        InteractionEvent.user_id.is_not(None), InteractionEvent.created_at >= since
    )
    subquery = impressed.union(interacted).subquery()
    result = await session.execute(select(func.count(func.distinct(subquery.c.user_id))))
    return result.scalar() or 0


async def ctr_by_surface(
    session: AsyncSession, since: datetime, *, locale: str | None = None
) -> list[dict[str, Any]]:
    impressions_query = (
        select(Impression.surface, func.count().label("n"))
        .where(Impression.served_at >= since)
        .group_by(Impression.surface)
    )
    clicks_query = (
        select(InteractionEvent.surface, func.count().label("n"))
        .where(InteractionEvent.event_type == "click", InteractionEvent.created_at >= since)
        .group_by(InteractionEvent.surface)
    )
    if locale:
        impressions_query = impressions_query.where(Impression.locale == locale)
        clicks_query = clicks_query.where(InteractionEvent.locale == locale)

    impressions = {row.surface: row.n for row in (await session.execute(impressions_query)).all()}
    clicks = {row.surface: row.n for row in (await session.execute(clicks_query)).all()}

    return [
        {
            "surface": surface,
            "impressions": impressions.get(surface, 0),
            "clicks": clicks.get(surface, 0),
        }
        for surface in sorted(set(impressions) | set(clicks))
    ]


async def ctr_by_ranking_policy(
    session: AsyncSession, since: datetime, *, locale: str | None = None
) -> list[dict[str, Any]]:
    """The Stage 5 A/B result: CTR for the heuristic ranker against the
    chronological control. Clicks are attributed to a policy through the
    exact impression that produced them (``InteractionEvent.impression_id``
    joined back to ``Impression.ranking_policy``), not through the click's
    own surface or timestamp - a click with no impression id cannot be
    attributed and is correctly excluded rather than guessed at.
    """
    impressions_query = (
        select(Impression.ranking_policy, func.count().label("n"))
        .where(Impression.served_at >= since)
        .group_by(Impression.ranking_policy)
    )
    clicks_query = (
        select(Impression.ranking_policy, func.count().label("n"))
        .select_from(InteractionEvent)
        .join(Impression, Impression.id == InteractionEvent.impression_id)
        .where(InteractionEvent.event_type == "click", InteractionEvent.created_at >= since)
        .group_by(Impression.ranking_policy)
    )
    if locale:
        impressions_query = impressions_query.where(Impression.locale == locale)
        clicks_query = clicks_query.where(InteractionEvent.locale == locale)

    impressions = {
        row.ranking_policy: row.n for row in (await session.execute(impressions_query)).all()
    }
    clicks = {row.ranking_policy: row.n for row in (await session.execute(clicks_query)).all()}

    return [
        {
            "ranking_policy": policy,
            "impressions": impressions.get(policy, 0),
            "clicks": clicks.get(policy, 0),
        }
        for policy in sorted(set(impressions) | set(clicks))
    ]


async def top_articles(
    session: AsyncSession, since: datetime, *, limit: int, locale: str | None = None
) -> list[dict[str, Any]]:
    query = (
        select(
            Article.id,
            Article.title,
            Article.language,
            func.count(Impression.id).label("impressions"),
        )
        .join(Impression, Impression.article_id == Article.id)
        .where(Impression.served_at >= since)
        .group_by(Article.id, Article.title, Article.language)
        .order_by(func.count(Impression.id).desc())
        .limit(limit)
    )
    if locale:
        query = query.where(Impression.locale == locale)
    rows = await session.execute(query)
    return [
        {"id": row.id, "title": row.title, "language": row.language, "impressions": row.impressions}
        for row in rows
    ]


async def source_performance(
    session: AsyncSession, since: datetime, *, limit: int, locale: str | None = None
) -> list[dict[str, Any]]:
    query = (
        select(Source.id, Source.name, func.count(Impression.id).label("impressions"))
        .join(Article, Article.source_id == Source.id)
        .join(Impression, Impression.article_id == Article.id)
        .where(Impression.served_at >= since)
        .group_by(Source.id, Source.name)
        .order_by(func.count(Impression.id).desc())
        .limit(limit)
    )
    if locale:
        query = query.where(Impression.locale == locale)
    rows = await session.execute(query)
    return [{"id": row.id, "name": row.name, "impressions": row.impressions} for row in rows]


# --------------------------------------------------------------------------
# Audit log
# --------------------------------------------------------------------------


async def record_action(
    session: AsyncSession,
    *,
    admin_user_id: UUID,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )
    await session.flush()


async def list_audit_log(session: AsyncSession, *, limit: int) -> list[AdminAuditLog]:
    query = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit)
    return list((await session.execute(query)).scalars().all())
