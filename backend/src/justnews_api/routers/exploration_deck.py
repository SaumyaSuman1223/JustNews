from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_beta_session
from justnews_api.repositories import flags as flags_repo
from justnews_api.routers.content import ArticleOut
from justnews_api.services import exploration_deck as service
from justnews_api.services.auth import Principal
from justnews_core.consent import UNCONSENTED_SESSION

router = APIRouter(prefix="/v1", tags=["exploration-deck"])


class DeckCardOut(BaseModel):
    article: ArticleOut
    topic_id: str
    impression_id: int | None


class DeckOut(BaseModel):
    cards: list[DeckCardOut]


@router.get("/exploration-deck", response_model=DeckOut)
async def get_exploration_deck(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    locale: str = Query(default="en"),
    languages: str | None = Query(default=None),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
    x_analytics_consent: str | None = Header(default=None, alias="x-analytics-consent"),
) -> DeckOut:
    if not await flags_repo.is_enabled(session, "exploration_deck"):
        # The kill switch: onboarding renders its degraded/empty state
        # rather than erroring, same as a thin corpus does.
        return DeckOut(cards=[])

    cards = await service.get_exploration_deck(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or UNCONSENTED_SESSION,
        locale=locale,
        languages=languages,
        log_impressions=x_analytics_consent == "granted",
    )
    return DeckOut(
        cards=[
            DeckCardOut(
                article=ArticleOut.from_row(card.article),
                topic_id=card.topic_id,
                impression_id=card.impression_id,
            )
            for card in cards
        ]
    )
