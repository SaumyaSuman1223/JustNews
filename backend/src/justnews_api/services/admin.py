"""Admin console business logic.

Every mutation here writes its own audit log row - that is the actual
implementation of "admin access is audit-logged" (CLAUDE.md), and it lives
here rather than in a decorator or middleware so the logged detail can be
specific to the action instead of a generic "admin called an endpoint".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import admin as repo
from justnews_api.repositories import content as content_repo
from justnews_api.repositories import feedback as feedback_repo
from justnews_api.repositories import topics as topics_repo
from justnews_api.repositories import users as users_repo
from justnews_api.services.topics import label_for
from justnews_core.errors import NotFoundError, ValidationError
from justnews_core.models import AdminAuditLog, Feedback, IngestRun, Topic, UserProfile

MAX_TAKEDOWN_REASON_LENGTH = 500
VALID_ROLES = ("reader", "admin")


async def takedown_article(
    session: AsyncSession, *, admin_user_id: UUID, article_id: int, reason: str
) -> content_repo.ArticleRow:
    reason = reason.strip()
    if not reason or len(reason) > MAX_TAKEDOWN_REASON_LENGTH:
        raise ValidationError(f"reason must be 1 to {MAX_TAKEDOWN_REASON_LENGTH} characters.")
    article = await repo.takedown_article(session, article_id, reason)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="article.takedown",
        target_type="article",
        target_id=str(article_id),
        details={"reason": reason},
    )
    row = await content_repo.get_article_including_removed(session, article_id)
    assert row is not None  # just fetched by id inside takedown_article
    return row


async def restore_article(
    session: AsyncSession, *, admin_user_id: UUID, article_id: int
) -> content_repo.ArticleRow:
    article = await repo.restore_article(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="article.restore",
        target_type="article",
        target_id=str(article_id),
    )
    row = await content_repo.get_article(session, article_id)
    assert row is not None  # just restored - it is visible to _base_query again
    return row


async def list_removed_articles(
    session: AsyncSession, *, limit: int = 50
) -> list[content_repo.ArticleRow]:
    return await repo.list_removed_articles(session, limit=limit)


async def list_source_health(session: AsyncSession) -> list[repo.SourceHealth]:
    return await repo.source_health(session)


async def list_recent_ingest_runs(session: AsyncSession, *, limit: int = 20) -> list[IngestRun]:
    return await repo.recent_ingest_runs(session, limit=limit)


async def set_user_role(
    session: AsyncSession, *, admin_user_id: UUID, target_user_id: UUID, role: str
) -> None:
    if role not in VALID_ROLES:
        raise ValidationError(f"role must be one of {VALID_ROLES}.")
    updated = await users_repo.set_role(session, target_user_id, role)
    if updated is None:
        raise NotFoundError(f"No user with id {target_user_id}.")
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="user.set_role",
        target_type="user",
        target_id=str(target_user_id),
        details={"role": role},
    )


async def list_users(
    session: AsyncSession, *, limit: int = 50, offset: int = 0, role: str | None = None
) -> list[UserProfile]:
    return await users_repo.list_profiles(session, limit=limit, offset=offset, role=role)


@dataclass(frozen=True, slots=True)
class AnalyticsOverview:
    since: datetime
    active_users: int
    ctr_by_surface: list[dict[str, Any]]
    ctr_by_ranking_policy: list[dict[str, Any]]
    top_articles: list[dict[str, Any]]
    top_sources: list[dict[str, Any]]


async def get_analytics_overview(
    session: AsyncSession, *, window_days: int = 7, locale: str | None = None
) -> AnalyticsOverview:
    if not 1 <= window_days <= 90:
        raise ValidationError("window_days must be between 1 and 90.")
    since = datetime.now(UTC) - timedelta(days=window_days)
    return AnalyticsOverview(
        since=since,
        active_users=await repo.active_user_count(session, since),
        ctr_by_surface=await repo.ctr_by_surface(session, since, locale=locale),
        ctr_by_ranking_policy=await repo.ctr_by_ranking_policy(session, since, locale=locale),
        top_articles=await repo.top_articles(session, since, limit=10, locale=locale),
        top_sources=await repo.source_performance(session, since, limit=10, locale=locale),
    )


async def list_audit_log(session: AsyncSession, *, limit: int = 100) -> list[AdminAuditLog]:
    return await repo.list_audit_log(session, limit=limit)


async def list_feedback(session: AsyncSession, *, limit: int = 100) -> list[Feedback]:
    return await feedback_repo.list_feedback(session, limit=limit)


@dataclass(frozen=True, slots=True)
class ActiveUsersBucket:
    bucket: datetime
    active_users: int


async def get_active_users_by_day(
    session: AsyncSession, *, window_days: int = 30, locale: str | None = None
) -> list[ActiveUsersBucket]:
    if not 1 <= window_days <= 90:
        raise ValidationError("window_days must be between 1 and 90.")
    since = datetime.now(UTC) - timedelta(days=window_days)
    rows = await repo.active_users_by_day(session, since, locale=locale)
    return [
        ActiveUsersBucket(bucket=row["bucket"], active_users=row["active_users"]) for row in rows
    ]


async def get_active_users_by_week(
    session: AsyncSession, *, window_weeks: int = 12, locale: str | None = None
) -> list[ActiveUsersBucket]:
    if not 1 <= window_weeks <= 52:
        raise ValidationError("window_weeks must be between 1 and 52.")
    since = datetime.now(UTC) - timedelta(weeks=window_weeks)
    rows = await repo.active_users_by_week(session, since, locale=locale)
    return [
        ActiveUsersBucket(bucket=row["bucket"], active_users=row["active_users"]) for row in rows
    ]


@dataclass(frozen=True, slots=True)
class TopicWithCount:
    topic: Topic
    label: str
    article_count: int


async def list_topics_for_admin(
    session: AsyncSession,
    *,
    parent: str | None,
    query: str | None,
    language: str,
) -> list[TopicWithCount]:
    topics = (
        await topics_repo.search_topics(session, query=query, language=language, limit=50)
        if query
        else await topics_repo.list_children(session, parent)
    )
    counts = await topics_repo.count_articles_by_topic(session, [topic.id for topic in topics])
    return [
        TopicWithCount(
            topic=topic, label=label_for(topic, language), article_count=counts.get(topic.id, 0)
        )
        for topic in topics
    ]


async def get_article_topics(
    session: AsyncSession, *, article_id: int, language: str
) -> list[tuple[Topic, str, bool]]:
    article = await content_repo.get_article_including_removed(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    assignments = await content_repo.get_article_topics(session, article_id)
    return [(topic, label_for(topic, language), is_primary) for topic, is_primary in assignments]


async def set_article_topics(
    session: AsyncSession,
    *,
    admin_user_id: UUID,
    article_id: int,
    topic_ids: list[str],
    primary_topic_id: str,
) -> None:
    if not topic_ids:
        raise ValidationError("An article must carry at least one topic.")
    if primary_topic_id not in topic_ids:
        raise ValidationError("primary_topic_id must be one of topic_ids.")
    article = await content_repo.get_article_including_removed(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    for topic_id in topic_ids:
        topic = await topics_repo.get_topic(session, topic_id)
        if topic is None or not topic.active:
            raise ValidationError(f"No active topic with id {topic_id}.")

    before = await content_repo.get_article_topics(session, article_id)
    await content_repo.set_article_topics(
        session,
        article_id,
        [(topic_id, topic_id == primary_topic_id) for topic_id in topic_ids],
    )
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="article_topics_override",
        target_type="article",
        target_id=str(article_id),
        details={
            "before": [topic.id for topic, _ in before],
            "after": topic_ids,
            "primary": primary_topic_id,
        },
    )
