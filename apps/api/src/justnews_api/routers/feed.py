from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import feed as service
from justnews_api.services.auth import Principal
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code

router = APIRouter(prefix="/v1", tags=["feed"])


class FeedPageOut(BaseModel):
    items: list[ArticleOut]
    next_cursor: str | None = Field(default=None)


@router.get("/feed", response_model=FeedPageOut)
async def get_feed(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
    languages: str | None = Query(
        default=None,
        examples=["en,es"],
        description="Overrides the reader's saved languages for this request.",
    ),
    locale: str = Query(default="en", description="UI locale the feed was rendered in."),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> FeedPageOut:
    normalised_locale = normalise_language_code(locale)
    if normalised_locale is None:
        raise ValidationError(f"Not a language code: {locale!r}")

    page = await service.get_feed_page(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or uuid.uuid4().hex,
        locale=normalised_locale,
        languages=languages,
        cursor=cursor,
        page_size=page_size,
    )
    return FeedPageOut(
        items=[ArticleOut.from_row(row) for row in page.items], next_cursor=page.next_cursor
    )
