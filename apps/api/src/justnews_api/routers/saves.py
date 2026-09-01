from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import saves as service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["saves"])


class SaveIn(BaseModel):
    article_id: int


class SaveOut(BaseModel):
    article: ArticleOut
    saved_at: datetime


class SavePageOut(BaseModel):
    items: list[SaveOut]
    next_cursor: str | None = Field(default=None)


def _to_out(saved: service.SavedArticle) -> SaveOut:
    return SaveOut(article=ArticleOut.from_row(saved.article), saved_at=saved.saved_at)


@router.post("/saves", response_model=SaveOut, status_code=status.HTTP_201_CREATED)
async def create_save(
    body: SaveIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> SaveOut:
    saved = await service.save_article(session, principal.user_id, body.article_id)
    return _to_out(saved)


@router.delete("/saves/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_save(
    article_id: int,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> None:
    await service.unsave_article(session, principal.user_id, article_id)


@router.get("/saves", response_model=SavePageOut)
async def list_saves(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=50),
) -> SavePageOut:
    page = await service.list_saved(session, principal.user_id, cursor=cursor, page_size=page_size)
    return SavePageOut(items=[_to_out(item) for item in page.items], next_cursor=page.next_cursor)
