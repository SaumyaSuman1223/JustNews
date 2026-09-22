from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.db import get_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import search as service
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code

router = APIRouter(prefix="/v1", tags=["search"])


class SearchTopicMatchOut(BaseModel):
    id: str
    label: str


class SearchSourceMatchOut(BaseModel):
    id: int
    name: str
    slug: str
    homepage_url: str


class SearchPageOut(BaseModel):
    items: list[ArticleOut]
    next_cursor: str | None = Field(default=None)
    total: int | None = Field(
        default=None,
        description=(
            "Total matches for this query. Present on the first page only - a "
            "later page would recount the same predicate for the same answer."
        ),
    )
    matched_topics: list[SearchTopicMatchOut] | None = Field(
        default=None,
        description="Topics whose name matches the query. Present on the first page only.",
    )
    matched_sources: list[SearchSourceMatchOut] | None = Field(
        default=None,
        description="Sources whose name matches the query. Present on the first page only.",
    )


@router.get("/search", response_model=SearchPageOut)
async def search_articles(
    q: str,
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["en,es"]),
    topic: str | None = Query(default=None, examples=["medtop:11000000"]),
    source: int | None = Query(default=None, description="Filter to one source's own id."),
    date: str | None = Query(
        default=None, description="One of 'day', 'week', 'month' - articles published within."
    ),
    language: str = Query(
        default="en", description="Interface language, for matched-topic labels."
    ),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=50),
) -> SearchPageOut:
    interface_language = normalise_language_code(language)
    if interface_language is None:
        raise ValidationError(f"Not a language code: {language!r}")
    # A failure here (DB down, upstream timeout) returns the standard 503
    # envelope like every other route - which is what lets the web tier fall
    # back to topic browse generically, without a search-specific error path.
    page = await service.search(
        session,
        query_text=q,
        languages=languages,
        topic_id=topic,
        source_id=source,
        date_window=date,
        interface_language=interface_language,
        cursor=cursor,
        page_size=page_size,
    )
    return SearchPageOut(
        items=[ArticleOut.from_row(row) for row in page.items],
        next_cursor=page.next_cursor,
        total=page.total,
        matched_topics=(
            [SearchTopicMatchOut(id=m.id, label=m.label) for m in page.matched_topics]
            if page.matched_topics is not None
            else None
        ),
        matched_sources=(
            [
                SearchSourceMatchOut(id=m.id, name=m.name, slug=m.slug, homepage_url=m.homepage_url)
                for m in page.matched_sources
            ]
            if page.matched_sources is not None
            else None
        ),
    )
