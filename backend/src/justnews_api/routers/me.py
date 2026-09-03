from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
from justnews_api.services import interactions as interactions_service
from justnews_api.services import users as service
from justnews_api.services.auth import Principal
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import UserProfile

router = APIRouter(prefix="/v1", tags=["me"])


class MeOut(BaseModel):
    id: str
    preferred_languages: list[str]
    role: str
    has_beta_access: bool
    created_at: datetime

    @classmethod
    def from_profile(cls, profile: UserProfile) -> MeOut:
        return cls(
            id=str(profile.id),
            preferred_languages=list(profile.preferred_languages),
            role=profile.role,
            has_beta_access=profile.role == "admin" or profile.invite_redeemed_at is not None,
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


class MeExportOut(BaseModel):
    profile: dict[str, Any]
    saves: list[dict[str, Any]]
    follows: list[dict[str, Any]]
    history: list[dict[str, Any]]


@router.get("/me/export", response_model=MeExportOut)
async def export_me(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> MeExportOut:
    export = await service.export_user_data(session, principal.user_id)
    return MeExportOut(
        profile=export.profile, saves=export.saves, follows=export.follows, history=export.history
    )


class LanguageMixOut(BaseModel):
    language: str
    count: int


class TopicMixOut(BaseModel):
    topic_id: str
    label: str
    count: int


class ReadingProfileOut(BaseModel):
    sampled: int
    languages: list[LanguageMixOut]
    topics: list[TopicMixOut]


@router.get("/me/reading-profile", response_model=ReadingProfileOut)
async def get_reading_profile(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
    language: str = Query(default="en"),
) -> ReadingProfileOut:
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")
    profile = await interactions_service.get_reading_profile(
        session, principal.user_id, language=code
    )
    return ReadingProfileOut(
        sampled=profile.sampled,
        languages=[
            LanguageMixOut(language=row.language, count=row.count) for row in profile.languages
        ],
        topics=[
            TopicMixOut(topic_id=row.topic_id, label=row.label, count=row.count)
            for row in profile.topics
        ],
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> None:
    await service.delete_account(session, principal.user_id)
