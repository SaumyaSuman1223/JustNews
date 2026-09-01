"""Public, unauthenticated content browsing.

No login, no personalisation, no interaction logging - anonymous, cacheable
reads over the corpus. The personalised, logged surface is ``/v1/feed``
(``routers/feed.py``), which requires a signed-in reader.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.db import get_session
from justnews_api.repositories import content as repo
from justnews_api.services import content as service
from justnews_core.models import StoryCluster

router = APIRouter(prefix="/v1", tags=["content"])


class ArticleOut(BaseModel):
    id: int
    title: str
    snippet: str | None
    image_url: str | None
    url: str = Field(description="Canonical publisher URL. Always link out to this.")
    language: str
    published_at: datetime
    source_name: str
    source_slug: str
    story_cluster_id: int | None

    @classmethod
    def from_row(cls, row: repo.ArticleRow) -> ArticleOut:
        return cls(
            id=row.id,
            title=row.title,
            snippet=row.snippet,
            image_url=row.image_url,
            url=row.url_canonical,
            language=row.language,
            published_at=row.published_at,
            source_name=row.source_name,
            source_slug=row.source_slug,
            story_cluster_id=row.story_cluster_id,
        )


class ArticlePageOut(BaseModel):
    items: list[ArticleOut]
    next_cursor: str | None = Field(
        default=None, description="Opaque keyset cursor. Pass back as ?cursor=. Never an offset."
    )


class StoryOut(BaseModel):
    id: int
    title: str
    article_count: int
    source_count: int
    language_count: int
    last_seen_at: datetime

    @classmethod
    def from_cluster(cls, cluster: StoryCluster) -> StoryOut:
        return cls(
            id=cluster.id,
            title=cluster.title,
            article_count=cluster.article_count,
            source_count=cluster.source_count,
            language_count=cluster.language_count,
            last_seen_at=cluster.last_seen_at,
        )


class StoryDetailOut(BaseModel):
    story: StoryOut
    articles: list[ArticleOut]


class StatsOut(BaseModel):
    articles: int
    sources: int
    story_clusters: int
    languages: int


@router.get("/articles", response_model=ArticlePageOut)
async def list_articles(
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["en,es"]),
    topic: str | None = Query(default=None, examples=["medtop:20000724"]),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
) -> ArticlePageOut:
    page = await service.get_article_page(
        session, languages=languages, cursor=cursor, page_size=page_size, topic=topic
    )
    return ArticlePageOut(
        items=[ArticleOut.from_row(row) for row in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, session: AsyncSession = Depends(get_session)) -> ArticleOut:
    return ArticleOut.from_row(await service.get_article(session, article_id))


@router.get("/stories", response_model=list[StoryOut])
async def list_stories(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
    min_sources: int = Query(default=2, ge=1, le=50),
) -> list[StoryOut]:
    clusters = await repo.list_story_clusters(session, limit=limit, min_sources=min_sources)
    return [StoryOut.from_cluster(cluster) for cluster in clusters]


@router.get("/stories/{story_id}", response_model=StoryDetailOut)
async def get_story(story_id: int, session: AsyncSession = Depends(get_session)) -> StoryDetailOut:
    detail = await service.get_story(session, story_id)
    return StoryDetailOut(
        story=StoryOut.from_cluster(detail.cluster),
        articles=[ArticleOut.from_row(row) for row in detail.articles],
    )


@router.get("/stats", response_model=StatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> StatsOut:
    return StatsOut(**await repo.corpus_stats(session))
