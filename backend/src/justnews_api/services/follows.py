"""Followed topics and sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import follows as repo
from justnews_core.errors import NotFoundError, ValidationError


@dataclass(frozen=True, slots=True)
class FollowedTopic:
    topic_id: str
    followed_at: datetime
    position: int


async def follow_topic(session: AsyncSession, user_id: UUID, topic_id: str) -> FollowedTopic:
    if not await repo.topic_exists(session, topic_id):
        raise NotFoundError(f"No topic with id {topic_id!r}.")
    row = await repo.create_follow(session, user_id, topic_id)
    return FollowedTopic(topic_id=row.topic_id, followed_at=row.created_at, position=row.position)


async def unfollow_topic(session: AsyncSession, user_id: UUID, topic_id: str) -> None:
    if not await repo.delete_follow(session, user_id, topic_id):
        raise NotFoundError(f"Not following topic {topic_id!r}.")


async def list_followed(session: AsyncSession, user_id: UUID) -> list[FollowedTopic]:
    rows = await repo.list_follows(session, user_id)
    return [
        FollowedTopic(topic_id=row.topic_id, followed_at=row.created_at, position=row.position)
        for row in rows
    ]


async def reorder_followed(session: AsyncSession, user_id: UUID, topic_ids: list[str]) -> None:
    """My Desk's drag-to-reorder: `topic_ids` must be exactly the reader's
    current follow set, in its new order - a partial list would leave the
    topics left out with no defined position at all."""
    current = await repo.list_followed_topic_ids(session, user_id)
    if set(topic_ids) != current or len(topic_ids) != len(current):
        raise ValidationError("The new order must include every followed topic exactly once.")
    await repo.reorder_follows(session, user_id, topic_ids)


@dataclass(frozen=True, slots=True)
class FollowedSource:
    source_id: int
    slug: str
    name: str
    followed_at: datetime


async def follow_source(session: AsyncSession, user_id: UUID, source_id: int) -> FollowedSource:
    if not await repo.source_exists(session, source_id):
        raise NotFoundError(f"No source with id {source_id}.")
    await repo.create_source_follow(session, user_id, source_id)
    # Read back for the display fields: the follow row carries only ids, and
    # the name and slug live on the source.
    row = await repo.get_source_follow(session, user_id, source_id)
    if row is None:  # pragma: no cover - the insert above just guaranteed it
        raise NotFoundError(f"No source with id {source_id}.")
    return FollowedSource(
        source_id=row.source_id, slug=row.slug, name=row.name, followed_at=row.created_at
    )


async def unfollow_source(session: AsyncSession, user_id: UUID, source_id: int) -> None:
    if not await repo.delete_source_follow(session, user_id, source_id):
        raise NotFoundError(f"Not following source {source_id}.")


async def list_followed_sources(session: AsyncSession, user_id: UUID) -> list[FollowedSource]:
    return [
        FollowedSource(
            source_id=row.source_id, slug=row.slug, name=row.name, followed_at=row.created_at
        )
        for row in await repo.list_source_follows(session, user_id)
    ]
