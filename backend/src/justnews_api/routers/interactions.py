from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import optional_user, require_user
from justnews_api.core.db import get_beta_session, get_public_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import interactions as service
from justnews_api.services.auth import Principal
from justnews_core.consent import UNCONSENTED_SESSION

router = APIRouter(prefix="/v1", tags=["interactions"])


class ClickIn(BaseModel):
    article_id: int
    surface: str
    position: int | None = None
    impression_id: int | None = None
    # Only ever sent by the exploration deck (surface="onboarding") - see
    # services.exploration_deck.record_deck_engagement.
    topic_id: str | None = None
    # The interface language the card was shown in, as on the impression.
    locale: str | None = None


class ViewIn(BaseModel):
    impression_id: int
    rendered_position: int = Field(ge=0, le=32767)
    slot: str


class ViewsIn(BaseModel):
    views: list[ViewIn] = Field(max_length=service.MAX_VIEWS_PER_REPORT)


class NotInterestedIn(BaseModel):
    article_id: int
    surface: str


class ShareIn(BaseModel):
    article_id: int
    surface: str
    topic_id: str | None = None


class HistoryOut(BaseModel):
    article: ArticleOut
    viewed_at: datetime


class HistoryPageOut(BaseModel):
    items: list[HistoryOut]
    next_cursor: str | None = Field(default=None)


@router.post("/history", status_code=status.HTTP_204_NO_CONTENT)
async def report_click(
    body: ClickIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> None:
    await service.report_click(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or UNCONSENTED_SESSION,
        article_id=body.article_id,
        surface=body.surface,
        position=body.position,
        impression_id=body.impression_id,
        topic_id=body.topic_id,
        locale=body.locale,
    )


@router.post("/clicks", status_code=status.HTTP_204_NO_CONTENT)
async def report_any_click(
    body: ClickIn,
    principal: Principal | None = Depends(optional_user),
    session: AsyncSession = Depends(get_public_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
    x_analytics_consent: str | None = Header(default=None, alias="x-analytics-consent"),
) -> None:
    """A click from any reader, signed in or not (ADR 0015) - the web app's
    one click endpoint. POST /v1/history stays for invited readers' older
    clients.

    Fails closed on consent, like the feed's impressions: without the header
    nothing is recorded. Signed out, a click also needs the impression it
    came from - see services.interactions.report_click.
    """
    if x_analytics_consent != "granted" or not x_session_id:
        return
    await service.report_click(
        session,
        user_id=principal.user_id if principal else None,
        session_id=x_session_id,
        article_id=body.article_id,
        surface=body.surface,
        position=body.position,
        impression_id=body.impression_id,
        topic_id=body.topic_id,
        locale=body.locale,
    )


@router.post("/impressions/views", status_code=status.HTTP_204_NO_CONTENT)
async def report_views(
    body: ViewsIn,
    principal: Principal | None = Depends(optional_user),
    session: AsyncSession = Depends(get_public_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
    x_analytics_consent: str | None = Header(default=None, alias="x-analytics-consent"),
) -> None:
    """Served cards that were actually on screen (migration 0020): the
    difference between "shown and passed over" and "never scrolled to".
    Consent-gated and fail-closed like every other logging route; only the
    caller's own impressions are recorded."""
    if x_analytics_consent != "granted" or not x_session_id:
        return
    await service.report_views(
        session,
        user_id=principal.user_id if principal else None,
        session_id=x_session_id,
        views=[
            service.ViewReport(
                impression_id=view.impression_id,
                rendered_position=view.rendered_position,
                slot=view.slot,
            )
            for view in body.views
        ],
    )


@router.get("/history", response_model=HistoryPageOut)
async def list_history(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=50),
) -> HistoryPageOut:
    page = await service.list_history(
        session, principal.user_id, cursor=cursor, page_size=page_size
    )
    return HistoryPageOut(
        items=[
            HistoryOut(article=ArticleOut.from_row(item.article), viewed_at=item.viewed_at)
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.post("/not-interested", status_code=status.HTTP_204_NO_CONTENT)
async def report_not_interested(
    body: NotInterestedIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> None:
    await service.report_not_interested(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or UNCONSENTED_SESSION,
        article_id=body.article_id,
        surface=body.surface,
    )


@router.post("/share", status_code=status.HTTP_204_NO_CONTENT)
async def report_share(
    body: ShareIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> None:
    await service.report_share(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or UNCONSENTED_SESSION,
        article_id=body.article_id,
        surface=body.surface,
        topic_id=body.topic_id,
    )


@router.delete("/not-interested/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def undo_not_interested(
    article_id: int,
    surface: str = Query(...),
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> None:
    """Reverses a not-interested mark. Records a new event rather than
    deleting the old one - see services.interactions.undo_not_interested."""
    await service.undo_not_interested(
        session,
        user_id=principal.user_id,
        session_id=x_session_id or UNCONSENTED_SESSION,
        article_id=article_id,
        surface=surface,
    )
