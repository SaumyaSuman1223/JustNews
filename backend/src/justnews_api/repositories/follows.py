"""Followed topics and sources: declarative per-user state, same shape as saves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Source, Topic, UserFollow, UserSourceFollow


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


@dataclass(frozen=True, slots=True)
class SourceFollowRow:
    source_id: int
    slug: str
    name: str
    created_at: datetime


async def create_source_follow(session: AsyncSession, user_id: UUID, source_id: int) -> datetime:
    stmt = (
        pg_insert(UserSourceFollow)
        .values(user_id=user_id, source_id=source_id)
        .on_conflict_do_nothing(constraint="uq_user_source_follows_user_source")
        .returning(UserSourceFollow.created_at)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        # Already followed. Idempotent, exactly like create_follow: a reader
        # pressing follow twice has expressed one preference, not an error.
        row = (
            await session.execute(
                select(UserSourceFollow.created_at).where(
                    UserSourceFollow.user_id == user_id,
                    UserSourceFollow.source_id == source_id,
                )
            )
        ).one()
    created_at: datetime = row.created_at
    return created_at


async def delete_source_follow(session: AsyncSession, user_id: UUID, source_id: int) -> bool:
    result = await session.execute(
        delete(UserSourceFollow).where(
            UserSourceFollow.user_id == user_id, UserSourceFollow.source_id == source_id
        )
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def source_exists(session: AsyncSession, source_id: int) -> bool:
    result = await session.execute(select(Source.id).where(Source.id == source_id))
    return result.first() is not None


def _source_follow_query() -> Select[tuple[int, str, str, datetime]]:
    return (
        select(UserSourceFollow.source_id, Source.slug, Source.name, UserSourceFollow.created_at)
        .join(Source, Source.id == UserSourceFollow.source_id)
        .order_by(UserSourceFollow.created_at.desc())
    )


async def get_source_follow(
    session: AsyncSession, user_id: UUID, source_id: int
) -> SourceFollowRow | None:
    """One follow, with the source's display fields joined in - the follow row
    itself only carries ids."""
    row = (
        await session.execute(
            _source_follow_query().where(
                UserSourceFollow.user_id == user_id, UserSourceFollow.source_id == source_id
            )
        )
    ).first()
    if row is None:
        return None
    return SourceFollowRow(source_id=row[0], slug=row[1], name=row[2], created_at=row[3])


async def list_source_follows(session: AsyncSession, user_id: UUID) -> list[SourceFollowRow]:
    result = await session.execute(
        _source_follow_query().where(UserSourceFollow.user_id == user_id)
    )
    return [
        SourceFollowRow(source_id=source_id, slug=slug, name=name, created_at=created_at)
        for source_id, slug, name, created_at in result.all()
    ]


async def list_followed_source_ids(session: AsyncSession, user_id: UUID) -> set[int]:
    result = await session.execute(
        select(UserSourceFollow.source_id).where(UserSourceFollow.user_id == user_id)
    )
    return set(result.scalars().all())
