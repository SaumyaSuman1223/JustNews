"""Impressions (served items, with propensity) and interaction events (what a
reader did about them). Two tables for two different shapes of fact: an
impression is written once, by the server, at serve time; an interaction
event is reported later, by the client, about something the reader did.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Impression, InteractionEvent


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
    """Articles explicitly marked not interesting - excluded from the feed."""
    result = await session.execute(
        select(InteractionEvent.article_id).where(
            InteractionEvent.user_id == user_id, InteractionEvent.event_type == "not_interested"
        )
    )
    return set(result.scalars().all())
