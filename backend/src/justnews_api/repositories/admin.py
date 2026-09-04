"""Read-side queries for the admin console: moderation, ops health, and
analytics. Nothing here is reachable except behind ``core.db.get_admin_session``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, func, select
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
    UserProfile,
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


async def _active_users_by_bucket(
    session: AsyncSession, since: datetime, granularity: str, *, locale: str | None
) -> list[dict[str, Any]]:
    """Shared by the DAU and WAU queries - a UNION of impressed and interacted
    (user_id, bucket) pairs, the same double-counting guard as
    ``active_user_count``, just grouped by bucket instead of collapsed to one
    total."""
    # The explicit 'UTC' argument matters: date_trunc's two-argument form
    # truncates in the session's timezone (whatever the connection happens to
    # be set to), which would silently shift bucket boundaries away from the
    # UTC dates CLAUDE.md requires everywhere else in this codebase.
    impressed = select(
        func.date_trunc(granularity, Impression.served_at, "UTC").label("bucket"),
        Impression.user_id.label("user_id"),
    ).where(Impression.user_id.is_not(None), Impression.served_at >= since)
    interacted = select(
        func.date_trunc(granularity, InteractionEvent.created_at, "UTC").label("bucket"),
        InteractionEvent.user_id.label("user_id"),
    ).where(InteractionEvent.user_id.is_not(None), InteractionEvent.created_at >= since)
    if locale:
        impressed = impressed.where(Impression.locale == locale)
        interacted = interacted.where(InteractionEvent.locale == locale)
    subquery = impressed.union(interacted).subquery()
    query = (
        select(subquery.c.bucket, func.count(func.distinct(subquery.c.user_id)))
        .group_by(subquery.c.bucket)
        .order_by(subquery.c.bucket)
    )
    rows = await session.execute(query)
    return [{"bucket": row[0], "active_users": row[1]} for row in rows]


async def active_users_by_day(
    session: AsyncSession, since: datetime, *, locale: str | None = None
) -> list[dict[str, Any]]:
    return await _active_users_by_bucket(session, since, "day", locale=locale)


async def active_users_by_week(
    session: AsyncSession, since: datetime, *, locale: str | None = None
) -> list[dict[str, Any]]:
    # Fixed weekly buckets (date_trunc('week', ...)), not a rolling 7-day
    # count - a true rolling WAU needs a correlated subquery per day, which
    # is more machinery than beta-scale traffic currently justifies.
    return await _active_users_by_bucket(session, since, "week", locale=locale)


async def retention_cohorts(
    session: AsyncSession, *, since: datetime, max_weeks: int, locale: str | None = None
) -> dict[str, Any]:
    """Weekly cohorts, keyed by the week a reader redeemed their invite (not
    account creation - that is when they actually started being able to use
    the product). ``weeks_since`` 0 is the cohort's own signup week, so every
    cohort has at least one active week by construction: it is the same
    "active" a reader was, at minimum, on the request that redeemed the
    invite and fetched their first feed.

    Two shapes are computed and returned together - cohort_size (how many
    readers joined that week) and an activity matrix (how many of them were
    still active N weeks later) - because a retention percentage with no
    denominator next to it invites exactly the "40 users is not a cohort"
    mistake ROADMAP.md warns about for num_groups.
    """
    cohorts = (
        select(
            UserProfile.id.label("user_id"),
            func.date_trunc("week", UserProfile.invite_redeemed_at, "UTC").label("cohort_week"),
        )
        .where(UserProfile.invite_redeemed_at.is_not(None), UserProfile.invite_redeemed_at >= since)
        .cte("cohorts")
    )

    impressed = select(
        Impression.user_id.label("user_id"),
        func.date_trunc("week", Impression.served_at, "UTC").label("active_week"),
    ).where(Impression.user_id.is_not(None))
    interacted = select(
        InteractionEvent.user_id.label("user_id"),
        func.date_trunc("week", InteractionEvent.created_at, "UTC").label("active_week"),
    ).where(InteractionEvent.user_id.is_not(None))
    if locale:
        impressed = impressed.where(Impression.locale == locale)
        interacted = interacted.where(InteractionEvent.locale == locale)
    activity = impressed.union(interacted).cte("activity")

    week_offset = func.floor(
        func.extract("epoch", activity.c.active_week - cohorts.c.cohort_week) / 604800
    ).cast(Integer)

    joined = (
        select(
            cohorts.c.cohort_week.label("cohort_week"),
            cohorts.c.user_id.label("user_id"),
            week_offset.label("week_offset"),
        )
        .select_from(cohorts.join(activity, activity.c.user_id == cohorts.c.user_id))
        .where(activity.c.active_week >= cohorts.c.cohort_week)
        .cte("joined")
    )

    activity_rows = await session.execute(
        select(
            joined.c.cohort_week,
            joined.c.week_offset,
            func.count(func.distinct(joined.c.user_id)),
        )
        .where(joined.c.week_offset <= max_weeks)
        .group_by(joined.c.cohort_week, joined.c.week_offset)
        .order_by(joined.c.cohort_week, joined.c.week_offset)
    )
    size_rows = await session.execute(
        select(cohorts.c.cohort_week, func.count())
        .group_by(cohorts.c.cohort_week)
        .order_by(cohorts.c.cohort_week)
    )

    return {
        "cohort_sizes": {row[0]: row[1] for row in size_rows},
        "activity": [
            {"cohort_week": row[0], "week_offset": row[1], "active_users": row[2]}
            for row in activity_rows
        ],
    }


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
# Per-user activity (the "watch a session" debugging view)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActivityEntry:
    kind: str  # "impression" | "interaction"
    occurred_at: datetime
    article_id: int
    article_title: str
    surface: str
    position: int | None
    ranking_policy: str | None
    event_type: str | None


async def user_activity(session: AsyncSession, user_id: UUID, *, limit: int) -> list[ActivityEntry]:
    """A merged, most-recent-first timeline of one reader's impressions and
    interactions - what an admin actually needs to debug "why did this
    reader see/do X", not a real session replay (no DOM, no screen capture,
    nothing beyond what this system already logs for Stage 6's sake)."""
    impressions = await session.execute(
        select(Impression, Article.title)
        .join(Article, Article.id == Impression.article_id)
        .where(Impression.user_id == user_id)
        .order_by(Impression.served_at.desc())
        .limit(limit)
    )
    interactions = await session.execute(
        select(InteractionEvent, Article.title)
        .join(Article, Article.id == InteractionEvent.article_id)
        .where(InteractionEvent.user_id == user_id)
        .order_by(InteractionEvent.created_at.desc())
        .limit(limit)
    )

    entries = [
        ActivityEntry(
            kind="impression",
            occurred_at=impression.served_at,
            article_id=impression.article_id,
            article_title=title,
            surface=impression.surface,
            position=impression.position,
            ranking_policy=impression.ranking_policy,
            event_type=None,
        )
        for impression, title in impressions
    ] + [
        ActivityEntry(
            kind="interaction",
            occurred_at=interaction.created_at,
            article_id=interaction.article_id,
            article_title=title,
            surface=interaction.surface,
            position=interaction.position,
            ranking_policy=None,
            event_type=interaction.event_type,
        )
        for interaction, title in interactions
    ]
    entries.sort(key=lambda entry: entry.occurred_at, reverse=True)
    return entries[:limit]


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
