"""Followed topics: declarative per-user state, same shape as saves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Topic, UserFollow


@dataclass(frozen=True, slots=True)
class FollowRow:
    topic_id: str
    created_at: datetime


async def create_follow(session: AsyncSession, user_id: UUID, topic_id: str) -> FollowRow:
    stmt = (
        pg_insert(UserFollow)
        .values(user_id=user_id, topic_id=topic_id)
        .on_conflict_do_nothing(constraint="uq_user_follows_user_topic")
        .returning(UserFollow.created_at)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        existing = await session.execute(
            select(UserFollow.created_at).where(
                UserFollow.user_id == user_id, UserFollow.topic_id == topic_id
            )
        )
        row = existing.one()
    return FollowRow(topic_id=topic_id, created_at=row.created_at)


async def delete_follow(session: AsyncSession, user_id: UUID, topic_id: str) -> bool:
    result = await session.execute(
        delete(UserFollow).where(UserFollow.user_id == user_id, UserFollow.topic_id == topic_id)
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def topic_exists(session: AsyncSession, topic_id: str) -> bool:
    result = await session.execute(select(Topic.id).where(Topic.id == topic_id))
    return result.first() is not None


async def list_follows(session: AsyncSession, user_id: UUID) -> list[FollowRow]:
    # Beta-scale reader follow counts (tens, not thousands) - no pagination.
    result = await session.execute(
        select(UserFollow)
        .where(UserFollow.user_id == user_id)
        .order_by(UserFollow.created_at.desc())
    )
    return [
        FollowRow(topic_id=follow.topic_id, created_at=follow.created_at)
        for follow in result.scalars().all()
    ]


async def list_followed_topic_ids(session: AsyncSession, user_id: UUID) -> set[str]:
    result = await session.execute(select(UserFollow.topic_id).where(UserFollow.user_id == user_id))
    return set(result.scalars().all())
