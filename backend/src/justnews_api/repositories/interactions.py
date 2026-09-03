"""Impressions (served items, with propensity) and interaction events (what a
reader did about them). Two tables for two different shapes of fact: an
impression is written once, by the server, at serve time; an interaction
event is reported later, by the client, about something the reader did.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from justnews_core.models import Article, ArticleTopic, Impression, InteractionEvent, Topic


@dataclass(frozen=True, slots=True)
class ImpressionToLog:
    article_id: int
    position: int
    propensity: float


async def log_impressions(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str,
    surface: str,
    locale: str,
    ranking_policy: str,
    items: list[ImpressionToLog],
) -> list[int]:
    """Bulk insert, one row per served item.

    Returns the new impression ids in the same order as ``items`` - Postgres'
    insertmanyvalues preserves that ordering under RETURNING - so the caller
    can hand each one back to the client to reference in a later click report.
    """
    if not items:
        return []
    result = await session.execute(
        insert(Impression).returning(Impression.id),
        [
            {
                "user_id": user_id,
                "session_id": session_id,
                "article_id": item.article_id,
                "position": item.position,
                "surface": surface,
                "locale": locale,
                "propensity": item.propensity,
                "ranking_policy": ranking_policy,
            }
            for item in items
        ],
    )
    return [row[0] for row in result.all()]


async def record_event(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str,
    article_id: int,
    event_type: str,
    surface: str,
    locale: str,
    impression_id: int | None = None,
    position: int | None = None,
    dwell_ms: int | None = None,
) -> None:
    session.add(
        InteractionEvent(
            user_id=user_id,
            session_id=session_id,
            article_id=article_id,
            impression_id=impression_id,
            event_type=event_type,
            position=position,
            surface=surface,
            locale=locale,
            dwell_ms=dwell_ms,
        )
    )
    await session.flush()


@dataclass(frozen=True, slots=True)
class HistoryRow:
    id: int
    article_id: int
    viewed_at: datetime


async def list_history(
    session: AsyncSession,
    user_id: UUID,
    *,
    limit: int,
    before_viewed_at: datetime | None,
    before_id: int | None,
) -> list[HistoryRow]:
    query = (
        select(InteractionEvent)
        .where(InteractionEvent.user_id == user_id, InteractionEvent.event_type == "click")
        .order_by(InteractionEvent.created_at.desc(), InteractionEvent.id.desc())
        .limit(limit)
    )
    if before_viewed_at is not None and before_id is not None:
        query = query.where(
            tuple_(InteractionEvent.created_at, InteractionEvent.id) < (before_viewed_at, before_id)
        )
    result = await session.execute(query)
    return [
        HistoryRow(id=event.id, article_id=event.article_id, viewed_at=event.created_at)
        for event in result.scalars().all()
    ]


async def excluded_article_ids(session: AsyncSession, user_id: UUID) -> set[int]:
    """Articles explicitly marked not interesting - excluded from the feed.

    Latest-event-wins, not "any not_interested row ever exists": undo is a
    new `not_interested_undo` event (migration 0009), not a deletion, so a
    reader who undoes a mark is excluded only until the NOT EXISTS below
    finds that later reversal - and is excluded again correctly if they
    re-mark the same article afterward.
    """
    later_undo = aliased(InteractionEvent)
    result = await session.execute(
        select(InteractionEvent.article_id).where(
            InteractionEvent.user_id == user_id,
            InteractionEvent.event_type == "not_interested",
            ~select(later_undo.id)
            .where(
                later_undo.user_id == InteractionEvent.user_id,
                later_undo.article_id == InteractionEvent.article_id,
                later_undo.event_type == "not_interested_undo",
                later_undo.created_at > InteractionEvent.created_at,
            )
            .exists(),
        )
    )
    return set(result.scalars().all())


@dataclass(frozen=True, slots=True)
class ReadingMixRow:
    key: str
    count: int


async def reading_mix(
    session: AsyncSession, user_id: UUID, *, sample_limit: int
) -> tuple[list[ReadingMixRow], list[ReadingMixRow]]:
    """Language and top-level-topic breakdowns over a reader's most recent
    clicks - one capped window, computed once and reused for both axes,
    rather than two independently-limited queries. A reader whose last N
    clicks skew heavily toward one language should see that skew reflected
    in the topic axis's sample too, not a differently-sized, silently
    unrelated slice of their history.

    Topics roll up to their level-1 ancestor (``path[1]`` - the array is
    root-first and 1-indexed in Postgres, so this is the top-level concept
    regardless of the primary topic's own depth) and count distinct
    articles, not tag rows - an article's other, non-primary topics do not
    inflate its own top-level bucket.
    """
    recent = (
        select(InteractionEvent.article_id)
        .where(InteractionEvent.user_id == user_id, InteractionEvent.event_type == "click")
        .order_by(InteractionEvent.created_at.desc(), InteractionEvent.id.desc())
        .limit(sample_limit)
        .subquery()
    )

    language_result = await session.execute(
        select(Article.language, func.count())
        .select_from(recent)
        .join(Article, Article.id == recent.c.article_id)
        .group_by(Article.language)
        .order_by(func.count().desc())
    )
    languages = [ReadingMixRow(key=row[0], count=row[1]) for row in language_result.all()]

    top_topic = aliased(Topic)
    topic_result = await session.execute(
        select(top_topic.id, func.count(func.distinct(recent.c.article_id)))
        .select_from(recent)
        .join(
            ArticleTopic,
            (ArticleTopic.article_id == recent.c.article_id) & (ArticleTopic.is_primary.is_(True)),
        )
        .join(Topic, Topic.id == ArticleTopic.topic_id)
        .join(top_topic, top_topic.id == Topic.path[1])
        .group_by(top_topic.id)
        .order_by(func.count(func.distinct(recent.c.article_id)).desc())
    )
    topics = [ReadingMixRow(key=row[0], count=row[1]) for row in topic_result.all()]

    return languages, topics
