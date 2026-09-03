from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_beta_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import interactions as service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["interactions"])


class ClickIn(BaseModel):
    article_id: int
    surface: str
    position: int | None = None
    impression_id: int | None = None


class NotInterestedIn(BaseModel):
    article_id: int
    surface: str


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
        session_id=x_session_id or uuid.uuid4().hex,
        article_id=body.article_id,
        surface=body.surface,
        position=body.position,
        impression_id=body.impression_id,
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
        session_id=x_session_id or uuid.uuid4().hex,
        article_id=body.article_id,
        surface=body.surface,
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
        session_id=x_session_id or uuid.uuid4().hex,
        article_id=article_id,
        surface=surface,
    )
