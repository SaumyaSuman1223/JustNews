"""Public, unauthenticated content browsing.

No login, no personalisation, no interaction logging - anonymous, cacheable
reads over the corpus. The personalised, logged surface is ``/v1/feed``
(``routers/feed.py``), which requires a signed-in reader.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core import cache
from justnews_api.core.db import get_session
from justnews_api.repositories import content as repo
from justnews_api.services import content as service
from justnews_api.services import topics as topics_service
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import StoryCluster

router = APIRouter(prefix="/v1", tags=["content"])


class CoverageOut(BaseModel):
    """Third-pass audit §21: "7 sources / 4 countries / 2 languages" - how
    widely the story this article belongs to is being covered, as of the last
    time the cluster changed. Real counts from `story_clusters`, never
    inferred: a cluster of one source is a real, honest `sources: 1`, not
    something the client has to guess from `story_cluster_id` alone."""

    articles: int
    sources: int
    languages: int
    countries: int
    #: Fourth-pass §19's `timeline` card variant: when this story first broke
    #: and when it was last added to, so a feed can say "developing" honestly
    #: rather than only naming how many sources are on it.
    first_seen_at: datetime
    last_seen_at: datetime


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
    # ADR 0013's Perspectives fact (industry/government/academic/investor/
    # consumer/public), already public on the Perspectives endpoint - this
    # is the same value, so a feed card can say "Industry press" the way a
    # topic's Perspectives module already does, without a second request.
    source_role: str | None = None
    story_cluster_id: int | None
    # `None` whenever `story_cluster_id` is null - most articles are not part
    # of a cluster at all. Never rebuild this from `story_cluster_id` on the
    # client: a cluster with a single source is a real cluster, so its
    # presence is not itself a signal of how many sources are covering it.
    coverage: CoverageOut | None = None

    @classmethod
    def from_row(cls, row: repo.ArticleRow) -> ArticleOut:
        coverage = (
            CoverageOut(
                articles=row.coverage.articles,
                sources=row.coverage.sources,
                languages=row.coverage.languages,
                countries=row.coverage.countries,
                first_seen_at=row.coverage.first_seen_at,
                last_seen_at=row.coverage.last_seen_at,
            )
            if row.coverage is not None
            else None
        )
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
            source_role=row.source_role,
            story_cluster_id=row.story_cluster_id,
            coverage=coverage,
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
    first_seen_at: datetime
    last_seen_at: datetime

    @classmethod
    def from_cluster(cls, cluster: StoryCluster) -> StoryOut:
        return cls(
            id=cluster.id,
            title=cluster.title,
            article_count=cluster.article_count,
            source_count=cluster.source_count,
            language_count=cluster.language_count,
            first_seen_at=cluster.first_seen_at,
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


class CategoryOut(BaseModel):
    id: str
    slug: str
    label: str


class PerspectiveSourceOut(BaseModel):
    id: int
    slug: str
    name: str
    homepage_url: str = Field(description="Always link out to the publisher.")


class PerspectiveGroupOut(BaseModel):
    role: str = Field(
        description="One of industry, government, academic, investor, consumer, public - "
        "the labels the perspectives copy shows, not an invented category name.",
    )
    article_count: int
    sources: list[PerspectiveSourceOut]


class StoryDetailOut(BaseModel):
    story: StoryOut
    articles: list[ArticleOut]
    # The cross-lingual split - "EN 1 · ES 3 · HI 2". Neither Ground News nor
    # Google News can show this, because neither clusters across languages.
    coverage: list[LanguageCoverageOut] = []
    # None when the cluster's articles don't agree on one primary topic.
    category: CategoryOut | None = None
    perspectives: list[PerspectiveGroupOut] = []


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
    source: int | None = Query(default=None, description="Filter to one publisher's own id."),
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
) -> ArticlePageOut:
    """Cache: the first page of each filter combination, 60s fresh + 300s
    stale (ADR 0014). Later pages are read through: a cursor is one reader's
    position, and caching every one would fill Redis with keys read once."""

    async def load(s: AsyncSession) -> dict[str, Any]:
        page = await service.get_article_page(
            s,
            languages=languages,
            cursor=cursor,
            page_size=page_size,
            topic=topic,
            country=country,
            source=source,
        )
        return ArticlePageOut(
            items=[ArticleOut.from_row(row) for row in page.items],
            next_cursor=page.next_cursor,
        ).model_dump(mode="json")

    if cursor is not None:
        return ArticlePageOut.model_validate(await load(session))
    key = f"articles:{languages or ''}:{topic or ''}:{country or ''}:{source or ''}:{page_size}"
    return ArticlePageOut.model_validate(
        await cache.read_through(key, ttl=60, stale=300, session=session, load=load)
    )


@router.get("/articles/top", response_model=list[ArticleOut])
async def top_articles(
    session: AsyncSession = Depends(get_session),
    languages: str | None = Query(default=None, examples=["en,es"]),
    limit: int = Query(default=14, ge=1, le=30),
) -> list[ArticleOut]:
    """What matters now, for a reader with no history to personalise from:
    recency x breadth of coverage x source trust, one article per story.

    Declared before ``/articles/{article_id}`` so "top" is never parsed as an
    id. Cache: 60s fresh + 300s stale (ADR 0014).
    """

    async def load(s: AsyncSession) -> list[dict[str, Any]]:
        rows = await service.get_top_articles(
            s, languages=service.parse_languages(languages), limit=limit
        )
        return [ArticleOut.from_row(row).model_dump(mode="json") for row in rows]

    payload = await cache.read_through(
        f"top:{languages or ''}:{limit}", ttl=60, stale=300, session=session, load=load
    )
    return [ArticleOut.model_validate(item) for item in payload]


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, session: AsyncSession = Depends(get_session)) -> ArticleOut:
    return ArticleOut.from_row(await service.get_article(session, article_id))


class ArticleTopicLinkOut(BaseModel):
    id: str
    label: str
    is_primary: bool


@router.get("/articles/{article_id}/topics", response_model=list[ArticleTopicLinkOut])
async def article_topics(
    article_id: int,
    session: AsyncSession = Depends(get_session),
    language: str = Query(default="en", description="Interface language, for the labels."),
) -> list[ArticleTopicLinkOut]:
    """What an article is filed under, primary first - the article page's
    topic links and its "more in this topic" (fifth pass F4). Cache: 120s."""
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")
    rows = await service.get_article_topics(session, article_id)
    return [
        ArticleTopicLinkOut(
            id=topic.id, label=topics_service.label_for(topic, code), is_primary=is_primary
        )
        for topic, is_primary in rows
    ]


@router.get("/stories", response_model=list[StoryOut])
async def list_stories(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
    min_sources: int = Query(default=2, ge=1, le=50),
) -> list[StoryOut]:
    clusters = await repo.list_story_clusters(session, limit=limit, min_sources=min_sources)
    return [StoryOut.from_cluster(cluster) for cluster in clusters]


@router.get("/stories/{story_id}", response_model=StoryDetailOut)
async def get_story(
    story_id: int,
    session: AsyncSession = Depends(get_session),
    language: str = Query(default="en"),
) -> StoryDetailOut:
    """Cache: 60s fresh + 300s stale (ADR 0014) - a developing story gains
    reports by the minute, so this stays short."""
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")

    async def load(s: AsyncSession) -> dict[str, Any]:
        return (await _story_out(s, story_id, code)).model_dump(mode="json")

    return StoryDetailOut.model_validate(
        await cache.read_through(
            f"story:{story_id}:{code}", ttl=60, stale=300, session=session, load=load
        )
    )


async def _story_out(session: AsyncSession, story_id: int, code: str) -> StoryDetailOut:
    detail = await service.get_story(session, story_id)
    return StoryDetailOut(
        story=StoryOut.from_cluster(detail.cluster),
        articles=[ArticleOut.from_row(row) for row in detail.articles],
        coverage=[LanguageCoverageOut.from_row(entry) for entry in detail.coverage],
        category=(
            CategoryOut(
                id=detail.category.id,
                slug=detail.category.slug,
                label=topics_service.label_for(detail.category, code),
            )
            if detail.category
            else None
        ),
        perspectives=[
            PerspectiveGroupOut(
                role=group.role,
                article_count=group.article_count,
                sources=[
                    PerspectiveSourceOut(
                        id=source.id,
                        slug=source.slug,
                        name=source.name,
                        homepage_url=source.homepage_url,
                    )
                    for source in group.sources
                ],
            )
            for group in detail.perspectives
        ],
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
    already exists for Stage 6's benefit. Cache: 60s fresh + 300s stale.
    """

    async def load(s: AsyncSession) -> list[dict[str, Any]]:
        rows = await service.get_trending(
            s, languages=service.parse_languages(languages), limit=limit
        )
        return [ArticleOut.from_row(row).model_dump(mode="json") for row in rows]

    payload = await cache.read_through(
        f"trending:{languages or ''}:{limit}", ttl=60, stale=300, session=session, load=load
    )
    return [ArticleOut.model_validate(item) for item in payload]


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
    language: str | None = Query(
        default=None,
        description=(
            "Onboarding's discovery mode: bounded to service.SOURCE_DISCOVERY_LIMIT, "
            "ranked by trust score within that language. Omit for the complete "
            "catalogue instead (search's source filter; audit §27) - alphabetical, "
            "unbounded."
        ),
    ),
) -> list[SourceOut]:
    rows = (
        await service.list_sources_for_language(session, language=language)
        if language is not None
        else await service.list_all_sources(session)
    )
    return [
        SourceOut(id=row.id, name=row.name, slug=row.slug, homepage_url=row.homepage_url)
        for row in rows
    ]


class SourceDetailOut(BaseModel):
    id: int
    name: str
    slug: str
    homepage_url: str
    country: str | None
    language: str
    # ADR 0013's editorial role, public on the Perspectives endpoint already.
    source_role: str | None
    article_count: int


@router.get("/sources/{slug}", response_model=SourceDetailOut)
async def source_detail(slug: str, session: AsyncSession = Depends(get_session)) -> SourceDetailOut:
    """One publisher. Cache: 300s fresh + 900s stale (ADR 0014)."""

    async def load(s: AsyncSession) -> dict[str, Any]:
        detail = await service.get_source(s, slug)
        source = detail.source
        return SourceDetailOut(
            id=source.id,
            name=source.name,
            slug=source.slug,
            homepage_url=source.homepage_url,
            country=source.country,
            language=source.language,
            source_role=source.source_role,
            article_count=detail.article_count,
        ).model_dump(mode="json")

    return SourceDetailOut.model_validate(
        await cache.read_through(f"source:{slug}", ttl=300, stale=900, session=session, load=load)
    )


@router.get("/stats", response_model=StatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> StatsOut:
    """Cache: 300s fresh + 900s stale (ADR 0014) - a count, not a headline."""

    async def load(s: AsyncSession) -> dict[str, Any]:
        return StatsOut(**await repo.corpus_stats(s)).model_dump(mode="json")

    return StatsOut.model_validate(
        await cache.read_through("stats", ttl=300, stale=900, session=session, load=load)
    )
