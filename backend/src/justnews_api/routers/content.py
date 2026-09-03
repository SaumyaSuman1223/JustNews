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
    # Exposed so a reader can follow the publisher; unlike source_trust_score
    # this is a plain identifier, not a judgement.
    source_id: int
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
            source_id=row.source_id,
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


class LanguageCoverageOut(BaseModel):
    language: str
    article_count: int
    source_count: int

    @classmethod
    def from_row(cls, row: repo.LanguageCoverage) -> LanguageCoverageOut:
        return cls(
            language=row.language,
            article_count=row.article_count,
            source_count=row.source_count,
        )


class StoryDetailOut(BaseModel):
    story: StoryOut
    articles: list[ArticleOut]
    # The cross-lingual split - "EN 1 · ES 3 · HI 2". Neither Ground News nor
    # Google News can show this, because neither clusters across languages.
    coverage: list[LanguageCoverageOut] = []


class BlindspotOut(BaseModel):
    """A story with coverage, none of it in a language the reader reads."""

    story: StoryOut
    coverage: list[LanguageCoverageOut]


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
    country: str | None = Query(
        default=None,
        max_length=2,
        examples=["IN"],
        description="Publisher country - what makes an edition regional, not just a language.",
    ),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
) -> ArticlePageOut:
    page = await service.get_article_page(
        session,
        languages=languages,
        cursor=cursor,
        page_size=page_size,
        topic=topic,
        country=country,
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
        coverage=[LanguageCoverageOut.from_row(entry) for entry in detail.coverage],
    )


@router.get("/blindspots", response_model=list[BlindspotOut])
async def blindspots(
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(
        default=None,
        examples=["en,hi"],
        description="The reader's languages. Stories covered in any of them are excluded.",
    ),
    limit: int = Query(default=6, ge=1, le=20),
) -> list[BlindspotOut]:
    """Stories being reported, but not in a language you read.

    Ground News's Blindspot reframed around language rather than politics -
    and answerable here only because clustering is cross-lingual, so "the same
    story, elsewhere" is a thing this corpus can actually identify.
    """
    requested = service.parse_languages(languages) or []
    found = await service.get_blindspots(session, languages=requested, limit=limit)
    return [
        BlindspotOut(
            story=StoryOut.from_cluster(item.cluster),
            coverage=[LanguageCoverageOut.from_row(entry) for entry in item.coverage],
        )
        for item in found
    ]


@router.get("/trending", response_model=list[ArticleOut])
async def trending(
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["en,hi"]),
    limit: int = Query(default=6, ge=1, le=20),
) -> list[ArticleOut]:
    """What readers are actually clicking, most-clicked first.

    Ranked on behaviour rather than recency - a rail that repeated the feed's
    own ordering would be decoration. Built from the interaction log that
    already exists for Stage 6's benefit.
    """
    rows = await service.get_trending(
        session, languages=service.parse_languages(languages), limit=limit
    )
    return [ArticleOut.from_row(row) for row in rows]


class EditionOut(BaseModel):
    code: str
    name: str
    language: str
    country: str | None
    is_default: bool


@router.get("/editions", response_model=list[EditionOut])
async def editions(
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["es"]),
) -> list[EditionOut]:
    """The regional views on offer - Google News' local-news equivalent."""
    rows = await service.list_editions(session, languages=service.parse_languages(languages))
    return [
        EditionOut(
            code=row.code,
            name=row.name,
            language=row.language,
            country=row.country,
            is_default=row.is_default,
        )
        for row in rows
    ]


class SourceOut(BaseModel):
    id: int
    name: str
    slug: str
    homepage_url: str


@router.get("/sources", response_model=list[SourceOut])
async def sources(
    session: AsyncSession = Depends(get_session),
    language: str = Query(...),
) -> list[SourceOut]:
    """A discovery list for onboarding - the handful of sources publishing in
    one language a new reader is most likely to already recognise. Not a
    directory: no pagination, no filtering beyond language, bounded to
    service.SOURCE_DISCOVERY_LIMIT."""
    rows = await service.list_sources_for_language(session, language=language)
    return [
        SourceOut(id=row.id, name=row.name, slug=row.slug, homepage_url=row.homepage_url)
        for row in rows
    ]


@router.get("/stats", response_model=StatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> StatsOut:
    return StatsOut(**await repo.corpus_stats(session))
