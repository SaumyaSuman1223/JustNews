from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.db import get_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import search as service

router = APIRouter(prefix="/v1", tags=["search"])


class SearchPageOut(BaseModel):
    items: list[ArticleOut]
    next_cursor: str | None = Field(default=None)


@router.get("/search", response_model=SearchPageOut)
async def search_articles(
    q: str,
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["en,es"]),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=50),
) -> SearchPageOut:
    # A failure here (DB down, upstream timeout) returns the standard 503
    # envelope like every other route - which is what lets the web tier fall
    # back to topic browse generically, without a search-specific error path.
    page = await service.search(
        session, query_text=q, languages=languages, cursor=cursor, page_size=page_size
    )
    return SearchPageOut(
        items=[ArticleOut.from_row(row) for row in page.items], next_cursor=page.next_cursor
    )
