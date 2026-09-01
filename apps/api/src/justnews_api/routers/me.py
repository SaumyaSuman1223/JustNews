from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
from justnews_api.services import users as service
from justnews_api.services.auth import Principal
from justnews_core.models import UserProfile

router = APIRouter(prefix="/v1", tags=["me"])


class MeOut(BaseModel):
    id: str
    preferred_languages: list[str]
    created_at: datetime

    @classmethod
    def from_profile(cls, profile: UserProfile) -> MeOut:
        return cls(
            id=str(profile.id),
            preferred_languages=list(profile.preferred_languages),
            created_at=profile.created_at,
        )


class MeUpdateIn(BaseModel):
    preferred_languages: list[str] = Field(min_length=1, max_length=service.MAX_LANGUAGES)


@router.get("/me", response_model=MeOut)
async def get_me(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> MeOut:
    profile = await service.get_or_create_profile(session, principal.user_id)
    return MeOut.from_profile(profile)


@router.patch("/me", response_model=MeOut)
async def update_me(
    body: MeUpdateIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> MeOut:
    profile = await service.update_profile(
        session, principal.user_id, preferred_languages=body.preferred_languages
    )
    return MeOut.from_profile(profile)
