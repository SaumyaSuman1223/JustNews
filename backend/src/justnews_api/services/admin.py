"""Admin console business logic.

Every mutation here writes its own audit log row - that is the actual
implementation of "admin access is audit-logged" (CLAUDE.md), and it lives
here rather than in a decorator or middleware so the logged detail can be
specific to the action instead of a generic "admin called an endpoint".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import admin as repo
from justnews_api.repositories import content as content_repo
from justnews_api.repositories import feedback as feedback_repo
from justnews_api.repositories import flags as flags_repo
from justnews_api.repositories import topics as topics_repo
from justnews_api.repositories import users as users_repo
from justnews_api.services.topics import label_for
from justnews_core.errors import NotFoundError, ValidationError
from justnews_core.models import AdminAuditLog, FeatureFlag, Feedback, IngestRun, Topic, UserProfile

MAX_TAKEDOWN_REASON_LENGTH = 500
VALID_ROLES = ("reader", "admin")
# "wire" is a valid assignment (it is what keeps Reuters/AP out of the
# perspective groups) even though services.perspectives.group_by_role never
# shows it as one - see ADR 0013.
VALID_SOURCE_ROLES = (
    "wire",
    "industry",
    "government",
    "academic",
    "investor",
    "consumer",
    "public",
)
FLAG_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,59}$")
FLAG_KEY_PATTERN_MESSAGE = (
    "key must start with a lowercase letter and contain only lowercase "
    "letters, digits and underscores, 3-60 characters."
)


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


async def set_source_role(
    session: AsyncSession, *, admin_user_id: UUID, source_id: int, role: str | None
) -> None:
    if role is not None and role not in VALID_SOURCE_ROLES:
        raise ValidationError(f"role must be one of {VALID_SOURCE_ROLES}, or null.")
    updated = await repo.set_source_role(session, source_id, role)
    if updated is None:
        raise NotFoundError(f"No source with id {source_id}.")
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="source.set_role",
        target_type="source",
        target_id=str(source_id),
        details={"role": role},
    )


async def list_users(
    session: AsyncSession, *, limit: int = 50, offset: int = 0, role: str | None = None
) -> list[UserProfile]:
    return await users_repo.list_profiles(session, limit=limit, offset=offset, role=role)


async def get_user_activity(
    session: AsyncSession, *, admin_user_id: UUID, target_user_id: UUID, limit: int = 50
) -> list[repo.ActivityEntry]:
    profile = await users_repo.get_profile(session, target_user_id)
    if profile is None:
        raise NotFoundError(f"No user with id {target_user_id}.")
    entries = await repo.user_activity(session, target_user_id, limit=limit)
    # Reading another reader's behavioural timeline is exactly the kind of
    # admin access CLAUDE.md requires be audit-logged - it is PII-adjacent
    # even though the table itself only ever stores an id, never an email.
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="user.view_activity",
        target_type="user",
        target_id=str(target_user_id),
    )
    return entries


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
class CohortWeek:
    week_offset: int
    active_users: int


@dataclass(frozen=True, slots=True)
class RetentionCohort:
    cohort_week: datetime
    cohort_size: int
    weeks: list[CohortWeek]


async def get_retention_cohorts(
    session: AsyncSession,
    *,
    window_weeks: int = 12,
    max_weeks_since: int = 8,
    locale: str | None = None,
) -> list[RetentionCohort]:
    if not 1 <= window_weeks <= 52:
        raise ValidationError("window_weeks must be between 1 and 52.")
    if not 1 <= max_weeks_since <= 26:
        raise ValidationError("max_weeks_since must be between 1 and 26.")
    since = datetime.now(UTC) - timedelta(weeks=window_weeks)
    raw = await repo.retention_cohorts(
        session, since=since, max_weeks=max_weeks_since, locale=locale
    )
    weeks_by_cohort: dict[datetime, list[CohortWeek]] = {}
    for row in raw["activity"]:
        weeks_by_cohort.setdefault(row["cohort_week"], []).append(
            CohortWeek(week_offset=row["week_offset"], active_users=row["active_users"])
        )
    return [
        RetentionCohort(
            cohort_week=cohort_week,
            cohort_size=size,
            weeks=weeks_by_cohort.get(cohort_week, []),
        )
        for cohort_week, size in sorted(raw["cohort_sizes"].items())
    ]


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


async def list_feature_flags(session: AsyncSession) -> list[FeatureFlag]:
    return await flags_repo.list_flags(session)


async def create_feature_flag(
    session: AsyncSession,
    *,
    admin_user_id: UUID,
    key: str,
    description: str,
    enabled: bool,
) -> FeatureFlag:
    if not FLAG_KEY_PATTERN.match(key):
        raise ValidationError(FLAG_KEY_PATTERN_MESSAGE)
    description = description.strip()
    if not description:
        raise ValidationError("description is required.")
    if await flags_repo.get_flag(session, key) is not None:
        raise ValidationError(f"A flag named {key!r} already exists.")
    flag = await flags_repo.create_flag(
        session, key=key, description=description, enabled=enabled, admin_user_id=admin_user_id
    )
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="feature_flag.create",
        target_type="feature_flag",
        target_id=key,
        details={"enabled": enabled, "description": description},
    )
    return flag


async def set_feature_flag(
    session: AsyncSession, *, admin_user_id: UUID, key: str, enabled: bool
) -> FeatureFlag:
    flag = await flags_repo.set_enabled(session, key, enabled=enabled, admin_user_id=admin_user_id)
    if flag is None:
        raise NotFoundError(f"No flag named {key!r}.")
    await repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="feature_flag.set",
        target_type="feature_flag",
        target_id=key,
        details={"enabled": enabled},
    )
    return flag
