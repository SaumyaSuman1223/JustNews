from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_beta_session
from justnews_api.services import follows as service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["follows"])


class FollowIn(BaseModel):
    topic_id: str


class FollowOut(BaseModel):
    topic_id: str
    followed_at: datetime


def _to_out(followed: service.FollowedTopic) -> FollowOut:
    return FollowOut(topic_id=followed.topic_id, followed_at=followed.followed_at)


@router.post("/follows", response_model=FollowOut, status_code=status.HTTP_201_CREATED)
async def create_follow(
    body: FollowIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> FollowOut:
    followed = await service.follow_topic(session, principal.user_id, body.topic_id)
    return _to_out(followed)


@router.delete("/follows/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_follow(
    topic_id: str,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> None:
    await service.unfollow_topic(session, principal.user_id, topic_id)


@router.get("/follows", response_model=list[FollowOut])
async def list_follows(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> list[FollowOut]:
    followed = await service.list_followed(session, principal.user_id)
    return [_to_out(item) for item in followed]


class SourceFollowIn(BaseModel):
    source_id: int


class SourceFollowOut(BaseModel):
    source_id: int
    slug: str
    name: str
    followed_at: datetime


def _source_out(followed: service.FollowedSource) -> SourceFollowOut:
    return SourceFollowOut(
        source_id=followed.source_id,
        slug=followed.slug,
        name=followed.name,
        followed_at=followed.followed_at,
    )


# Sources live under /follows/sources rather than replacing /follows, so the
# topic routes keep their existing shape and no client breaks.
@router.post(
    "/follows/sources", response_model=SourceFollowOut, status_code=status.HTTP_201_CREATED
)
async def create_source_follow(
    body: SourceFollowIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> SourceFollowOut:
    return _source_out(await service.follow_source(session, principal.user_id, body.source_id))


@router.delete("/follows/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_follow(
    source_id: int,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> None:
    await service.unfollow_source(session, principal.user_id, source_id)


@router.get("/follows/sources", response_model=list[SourceFollowOut])
async def list_source_follows(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
) -> list[SourceFollowOut]:
    return [
        _source_out(item)
        for item in await service.list_followed_sources(session, principal.user_id)
    ]
