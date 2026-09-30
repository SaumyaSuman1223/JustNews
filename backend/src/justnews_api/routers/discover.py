from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core import cache
from justnews_api.core.auth import optional_user
from justnews_api.core.db import get_public_session
from justnews_api.routers.content import ArticleOut
from justnews_api.routers.feed import RankReasonOut
from justnews_api.services import discover as service
from justnews_api.services.auth import Principal
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, parse_topics
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code

router = APIRouter(prefix="/v1", tags=["discover"])


class DiscoverItemOut(BaseModel):
    article: ArticleOut
    #: Hand it back with a click or a view report; null when nothing was
    #: logged (no analytics consent).
    impression_id: int | None
    reason: RankReasonOut | None = None
    #: The card's place in the whole feed - the position a click reports.
    position: int


class DiscoverPageOut(BaseModel):
    items: list[DiscoverItemOut]
    next_cursor: str | None = Field(default=None)


def _out(page: service.DiscoverPage) -> DiscoverPageOut:
    return DiscoverPageOut(
        items=[
            DiscoverItemOut(
                article=ArticleOut.from_row(item.article),
                impression_id=item.impression_id,
                reason=(
                    RankReasonOut(kind=item.reason.kind, topic_id=item.reason.topic_id)
                    if item.reason is not None
                    else None
                ),
                position=item.position,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get("/discover", response_model=DiscoverPageOut)
async def discover(
    view: Literal["for_you", "top", "topic"] = Query(default="top"),
    topic: str | None = Query(default=None, description="The topic view's IPTC concept id."),
    interests: str | None = Query(
        default=None,
        description="Signed out: the reader's topic picks, weighed like follows.",
    ),
    history: str | None = Query(
        default=None,
        description="Signed out: article ids this device opened recently, newest first.",
    ),
    languages: str | None = Query(default=None, examples=["en,hi"]),
    locale: str = Query(default="en", description="UI locale the page is rendered in."),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    principal: Principal | None = Depends(optional_user),
    session: AsyncSession = Depends(get_public_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
    x_analytics_consent: str | None = Header(default=None, alias="x-analytics-consent"),
) -> DiscoverPageOut:
    """One page of a Discover view, ranked by ranker v2 (ADR 0015), for any
    reader.

    Cache: the first page for a signed-out reader with no consent, no device
    history and no topic picks is the same for everyone who asks - 60s fresh
    and 300s stale, like the article list it replaces (ADR 0014). Everything
    else is personal or logs impressions, and is never cached.
    """
    code = normalise_language_code(locale)
    if code is None:
        raise ValidationError(f"Not a language code: {locale!r}")
    # Fails closed, like the feed: an absent header is not consent.
    log = x_analytics_consent == "granted" and bool(x_session_id)
    history_ids = service.parse_history(history)
    interest_ids = parse_topics(interests) or []

    async def load(s: AsyncSession) -> dict[str, Any]:
        page = await service.get_page(
            s,
            view=view,
            topic=topic,
            interests=interest_ids,
            history=history_ids,
            languages=languages,
            locale=code,
            cursor=cursor,
            page_size=page_size,
            user_id=principal.user_id if principal else None,
            session_id=x_session_id if log else None,
            log=log,
        )
        return _out(page).model_dump(mode="json")

    shared = principal is None and not log and not history_ids and not interest_ids
    if shared and cursor is None:
        key = f"discover:{view}:{topic or ''}:{languages or ''}:{code}:{page_size}"
        return DiscoverPageOut.model_validate(
            await cache.read_through(key, ttl=60, stale=300, session=session, load=load)
        )
    return DiscoverPageOut.model_validate(await load(session))
