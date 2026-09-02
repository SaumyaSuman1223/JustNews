from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import optional_user
from justnews_api.core.db import get_public_session
from justnews_api.routers.content import ArticleOut
from justnews_api.routers.feed import FeedItemOut, FeedPageOut
from justnews_api.services import explore as service
from justnews_api.services.auth import Principal
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code

router = APIRouter(prefix="/v1", tags=["explore"])


@router.get("/explore", response_model=FeedPageOut)
async def get_explore(
    principal: Principal | None = Depends(optional_user),
    session: AsyncSession = Depends(get_public_session),
    languages: str | None = Query(default=None, examples=["en,es"]),
    locale: str = Query(default="en", description="UI locale the page was rendered in."),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> FeedPageOut:
    """Latest news, ranked, no sign-in required.

    Unlike /v1/feed this is not behind the beta gate or `require_user`: a
    signed-out visitor is exactly who explore is for, and their impressions
    are logged against their browsing session rather than a user id.
    """
    normalised_locale = normalise_language_code(locale)
    if normalised_locale is None:
        raise ValidationError(f"Not a language code: {locale!r}")

    page = await service.get_explore_page(
        session,
        user_id=principal.user_id if principal else None,
        session_id=x_session_id or uuid.uuid4().hex,
        locale=normalised_locale,
        languages=languages,
        cursor=cursor,
        page_size=page_size,
    )
    return FeedPageOut(
        items=[
            FeedItemOut(article=ArticleOut.from_row(item.article), impression_id=item.impression_id)
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )
