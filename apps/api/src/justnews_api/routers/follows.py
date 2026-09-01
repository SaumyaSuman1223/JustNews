from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
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
    session: AsyncSession = Depends(get_user_session),
) -> FollowOut:
    followed = await service.follow_topic(session, principal.user_id, body.topic_id)
    return _to_out(followed)


@router.delete("/follows/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_follow(
    topic_id: str,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> None:
    await service.unfollow_topic(session, principal.user_id, topic_id)


@router.get("/follows", response_model=list[FollowOut])
async def list_follows(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> list[FollowOut]:
    followed = await service.list_followed(session, principal.user_id)
    return [_to_out(item) for item in followed]
