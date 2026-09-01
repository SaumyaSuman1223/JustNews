"""Followed topics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import follows as repo
from justnews_core.errors import NotFoundError


@dataclass(frozen=True, slots=True)
class FollowedTopic:
    topic_id: str
    followed_at: datetime


async def follow_topic(session: AsyncSession, user_id: UUID, topic_id: str) -> FollowedTopic:
    if not await repo.topic_exists(session, topic_id):
        raise NotFoundError(f"No topic with id {topic_id!r}.")
    row = await repo.create_follow(session, user_id, topic_id)
    return FollowedTopic(topic_id=row.topic_id, followed_at=row.created_at)


async def unfollow_topic(session: AsyncSession, user_id: UUID, topic_id: str) -> None:
    if not await repo.delete_follow(session, user_id, topic_id):
        raise NotFoundError(f"Not following topic {topic_id!r}.")


async def list_followed(session: AsyncSession, user_id: UUID) -> list[FollowedTopic]:
    rows = await repo.list_follows(session, user_id)
    return [FollowedTopic(topic_id=row.topic_id, followed_at=row.created_at) for row in rows]
