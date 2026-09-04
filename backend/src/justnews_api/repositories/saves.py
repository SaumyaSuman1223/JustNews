"""Bookmarks: declarative per-user state, not an event log."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, UserSave


@dataclass(frozen=True, slots=True)
class SaveRow:
    article_id: int
    created_at: datetime
    id: int


async def create_save(session: AsyncSession, user_id: UUID, article_id: int) -> SaveRow:
    # ON CONFLICT DO NOTHING: saving twice is a no-op, not a 409 - the client
    # does not need to know whether this was the first save or the fifth.
    stmt = (
        pg_insert(UserSave)
        .values(user_id=user_id, article_id=article_id)
        .on_conflict_do_nothing(constraint="uq_user_saves_user_article")
        .returning(UserSave.id, UserSave.created_at)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        # Already existed - fetch the original so the response is still accurate.
        existing = await session.execute(
            select(UserSave.id, UserSave.created_at).where(
                UserSave.user_id == user_id, UserSave.article_id == article_id
            )
        )
        row = existing.one()
    return SaveRow(article_id=article_id, created_at=row.created_at, id=row.id)


async def delete_save(session: AsyncSession, user_id: UUID, article_id: int) -> bool:
    result = await session.execute(
        delete(UserSave).where(UserSave.user_id == user_id, UserSave.article_id == article_id)
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def list_saves(
    session: AsyncSession,
    user_id: UUID,
    *,
    limit: int,
    before_created_at: datetime | None,
    before_id: int | None,
) -> list[SaveRow]:
    query = (
        select(UserSave)
        .where(UserSave.user_id == user_id)
        .order_by(UserSave.created_at.desc(), UserSave.id.desc())
        .limit(limit)
    )
    if before_created_at is not None and before_id is not None:
        query = query.where(
            tuple_(UserSave.created_at, UserSave.id) < (before_created_at, before_id)
        )
    result = await session.execute(query)
    return [
        SaveRow(article_id=save.article_id, created_at=save.created_at, id=save.id)
        for save in result.scalars().all()
    ]


async def is_saved(session: AsyncSession, user_id: UUID, article_id: int) -> bool:
    result = await session.execute(
        select(UserSave.id).where(UserSave.user_id == user_id, UserSave.article_id == article_id)
    )
    return result.first() is not None


async def saved_article_ids_in_topic(
    session: AsyncSession, user_id: UUID, topic_id: str
) -> set[int]:
    """Backs the exploration deck's UserFollow bridge
    (services.exploration_deck): a save is a declarative bookmark, not an
    InteractionEvent, so counting a reader's topic engagement toward that
    bridge's threshold has to look here too, not only at click/share
    events."""
    result = await session.execute(
        select(UserSave.article_id.distinct())
        .join(ArticleTopic, ArticleTopic.article_id == UserSave.article_id)
        .where(UserSave.user_id == user_id, ArticleTopic.topic_id == topic_id)
    )
    return set(result.scalars().all())
