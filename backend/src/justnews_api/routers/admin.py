"""The admin console API. Every route requires ``get_admin_session`` -
signed in, role ``admin`` - and every mutation writes its own audit log row.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_admin_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import admin as service
from justnews_api.services import invites as invites_service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# --- moderation -----------------------------------------------------------


class TakedownIn(BaseModel):
    reason: str


@router.post("/articles/{article_id}/takedown", response_model=ArticleOut)
async def takedown_article(
    article_id: int,
    body: TakedownIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_admin_session),
) -> ArticleOut:
    row = await service.takedown_article(
        session, admin_user_id=principal.user_id, article_id=article_id, reason=body.reason
    )
    return ArticleOut.from_row(row)


@router.post("/articles/{article_id}/restore", response_model=ArticleOut)
async def restore_article(
    article_id: int,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_admin_session),
) -> ArticleOut:
    row = await service.restore_article(
        session, admin_user_id=principal.user_id, article_id=article_id
    )
    return ArticleOut.from_row(row)


@router.get("/articles/removed", response_model=list[ArticleOut])
async def list_removed_articles(
    session: AsyncSession = Depends(get_admin_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ArticleOut]:
    rows = await service.list_removed_articles(session, limit=limit)
    return [ArticleOut.from_row(row) for row in rows]


# --- ops health -------------------------------------------------------------


class SourceHealthOut(BaseModel):
    id: int
    name: str
    slug: str
    language: str
    active: bool
    feed_count: int
    failing_feed_count: int
    last_success_at: datetime | None
    article_count: int


@router.get("/sources", response_model=list[SourceHealthOut])
async def list_source_health(
    session: AsyncSession = Depends(get_admin_session),
) -> list[SourceHealthOut]:
    rows = await service.list_source_health(session)
    return [SourceHealthOut(**dataclasses.asdict(row)) for row in rows]


class IngestRunOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    trigger: str
    feeds_total: int
    feeds_ok: int
    feeds_not_modified: int
    feeds_failed: int
    entries_seen: int
    articles_new: int
    articles_duplicate: int
    articles_clustered: int
    articles_enriched: int
    gnews_calls: int
    deadline_reached: bool
    error: str | None


@router.get("/ingest-runs", response_model=list[IngestRunOut])
async def list_ingest_runs(
    session: AsyncSession = Depends(get_admin_session),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[IngestRunOut]:
    runs = await service.list_recent_ingest_runs(session, limit=limit)
    return [IngestRunOut.model_validate(run, from_attributes=True) for run in runs]


# --- users ------------------------------------------------------------------


class UserOut(BaseModel):
    id: str
    role: str
    preferred_languages: list[str]
    invite_redeemed_at: datetime | None
    created_at: datetime


class SetRoleIn(BaseModel):
    role: str


@router.get("/users", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_admin_session),
    role: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UserOut]:
    profiles = await service.list_users(session, limit=limit, offset=offset, role=role)
    return [
        UserOut(
            id=str(profile.id),
            role=profile.role,
            preferred_languages=list(profile.preferred_languages),
            invite_redeemed_at=profile.invite_redeemed_at,
            created_at=profile.created_at,
        )
        for profile in profiles
    ]


@router.post("/users/{user_id}/role", status_code=204)
async def set_user_role(
    user_id: str,
    body: SetRoleIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_admin_session),
) -> None:
    await service.set_user_role(
        session, admin_user_id=principal.user_id, target_user_id=UUID(user_id), role=body.role
    )


# --- analytics ----------------------------------------------------------------


class SurfaceCtrOut(BaseModel):
    surface: str
    impressions: int
    clicks: int


class RankingPolicyCtrOut(BaseModel):
    ranking_policy: str
    impressions: int
    clicks: int


class TopArticleOut(BaseModel):
    id: int
    title: str
    language: str
    impressions: int


class TopSourceOut(BaseModel):
    id: int
    name: str
    impressions: int


class AnalyticsOverviewOut(BaseModel):
    since: datetime
    active_users: int
    ctr_by_surface: list[SurfaceCtrOut]
    # The Stage 5 A/B result: heuristic ranker vs chronological control.
    ctr_by_ranking_policy: list[RankingPolicyCtrOut]
    top_articles: list[TopArticleOut]
    top_sources: list[TopSourceOut]


@router.get("/analytics/overview", response_model=AnalyticsOverviewOut)
async def analytics_overview(
    session: AsyncSession = Depends(get_admin_session),
    window_days: int = Query(default=7, ge=1, le=90),
    locale: str | None = Query(default=None),
) -> AnalyticsOverviewOut:
    overview = await service.get_analytics_overview(session, window_days=window_days, locale=locale)
    return AnalyticsOverviewOut(
        since=overview.since,
        active_users=overview.active_users,
        ctr_by_surface=[SurfaceCtrOut(**row) for row in overview.ctr_by_surface],
        ctr_by_ranking_policy=[
            RankingPolicyCtrOut(**row) for row in overview.ctr_by_ranking_policy
        ],
        top_articles=[TopArticleOut(**row) for row in overview.top_articles],
        top_sources=[TopSourceOut(**row) for row in overview.top_sources],
    )


class ActiveUsersBucketOut(BaseModel):
    bucket: datetime
    active_users: int


@router.get("/analytics/dau", response_model=list[ActiveUsersBucketOut])
async def daily_active_users(
    session: AsyncSession = Depends(get_admin_session),
    window_days: int = Query(default=30, ge=1, le=90),
    locale: str | None = Query(default=None),
) -> list[ActiveUsersBucketOut]:
    buckets = await service.get_active_users_by_day(session, window_days=window_days, locale=locale)
    return [ActiveUsersBucketOut(bucket=b.bucket, active_users=b.active_users) for b in buckets]


@router.get("/analytics/wau", response_model=list[ActiveUsersBucketOut])
async def weekly_active_users(
    session: AsyncSession = Depends(get_admin_session),
    window_weeks: int = Query(default=12, ge=1, le=52),
    locale: str | None = Query(default=None),
) -> list[ActiveUsersBucketOut]:
    buckets = await service.get_active_users_by_week(
        session, window_weeks=window_weeks, locale=locale
    )
    return [ActiveUsersBucketOut(bucket=b.bucket, active_users=b.active_users) for b in buckets]


# --- taxonomy ---------------------------------------------------------------


class AdminTopicOut(BaseModel):
    id: str
    label: str
    level: int
    article_count: int


class ArticleTopicOut(BaseModel):
    id: str
    label: str
    is_primary: bool


class ArticleTopicsIn(BaseModel):
    topic_ids: list[str]
    primary_topic_id: str


@router.get("/topics", response_model=list[AdminTopicOut])
async def list_topics(
    session: AsyncSession = Depends(get_admin_session),
    parent: str | None = Query(default=None),
    q: str | None = Query(default=None),
    language: str = Query(default="en"),
) -> list[AdminTopicOut]:
    topics = await service.list_topics_for_admin(session, parent=parent, query=q, language=language)
    return [
        AdminTopicOut(
            id=item.topic.id,
            label=item.label,
            level=item.topic.level,
            article_count=item.article_count,
        )
        for item in topics
    ]


@router.get("/articles/{article_id}/topics", response_model=list[ArticleTopicOut])
async def get_article_topics(
    article_id: int,
    session: AsyncSession = Depends(get_admin_session),
    language: str = Query(default="en"),
) -> list[ArticleTopicOut]:
    assignments = await service.get_article_topics(
        session, article_id=article_id, language=language
    )
    return [
        ArticleTopicOut(id=topic.id, label=label, is_primary=is_primary)
        for topic, label, is_primary in assignments
    ]


@router.put("/articles/{article_id}/topics", status_code=204)
async def set_article_topics(
    article_id: int,
    body: ArticleTopicsIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_admin_session),
) -> None:
    await service.set_article_topics(
        session,
        admin_user_id=principal.user_id,
        article_id=article_id,
        topic_ids=body.topic_ids,
        primary_topic_id=body.primary_topic_id,
    )


# --- audit log ----------------------------------------------------------------


class AuditLogEntryOut(BaseModel):
    id: int
    admin_user_id: str
    action: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any] | None
    created_at: datetime


@router.get("/audit-log", response_model=list[AuditLogEntryOut])
async def list_audit_log(
    session: AsyncSession = Depends(get_admin_session),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLogEntryOut]:
    entries = await service.list_audit_log(session, limit=limit)
    return [
        AuditLogEntryOut(
            id=entry.id,
            admin_user_id=str(entry.admin_user_id),
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


# --- beta invites ---------------------------------------------------------


class InviteCreateIn(BaseModel):
    note: str | None = None
    max_uses: int = Field(default=1, ge=1, le=10_000)
    expires_at: datetime | None = None


class InviteOut(BaseModel):
    code: str
    note: str | None
    max_uses: int
    uses: int
    expires_at: datetime | None
    created_at: datetime


@router.post("/invites", response_model=InviteOut, status_code=201)
async def create_invite(
    body: InviteCreateIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_admin_session),
) -> InviteOut:
    invite = await invites_service.create_invite(
        session,
        admin_user_id=principal.user_id,
        note=body.note,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
    )
    return InviteOut.model_validate(invite, from_attributes=True)


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(session: AsyncSession = Depends(get_admin_session)) -> list[InviteOut]:
    invites = await invites_service.list_invites(session)
    return [InviteOut.model_validate(invite, from_attributes=True) for invite in invites]


# --- feedback -----------------------------------------------------------


class FeedbackEntryOut(BaseModel):
    id: int
    user_id: str | None
    locale: str
    path: str | None
    message: str
    created_at: datetime


@router.get("/feedback", response_model=list[FeedbackEntryOut])
async def list_feedback(
    session: AsyncSession = Depends(get_admin_session),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[FeedbackEntryOut]:
    entries = await service.list_feedback(session, limit=limit)
    return [
        FeedbackEntryOut(
            id=entry.id,
            user_id=str(entry.user_id) if entry.user_id else None,
            locale=entry.locale,
            path=entry.path,
            message=entry.message,
            created_at=entry.created_at,
        )
        for entry in entries
    ]
