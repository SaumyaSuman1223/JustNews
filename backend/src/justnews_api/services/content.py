"""Public, unauthenticated content service.

Anonymous browsing over the corpus - no ranking, no personalisation. That is
``services/feed.py``, which requires a signed-in reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as repo
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import NotFoundError, ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import Edition, Source, StoryCluster

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class ArticlePage:
    items: list[repo.ArticleRow]
    next_cursor: str | None


def parse_languages(raw: str | None) -> list[str] | None:
    """``"en,es,ar"`` to a validated list. No reader receives a language they
    did not ask for, so junk here is rejected rather than ignored."""
    if not raw:
        return None
    codes: list[str] = []
    for part in raw.split(","):
        code = normalise_language_code(part)
        if code is None:
            raise ValidationError(f"Not a language code: {part.strip()!r}")
        if code not in codes:
            codes.append(code)
    return codes or None


async def get_article_page(
    session: AsyncSession,
    *,
    languages: str | None = None,
    cursor: str | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    topic: str | None = None,
    country: str | None = None,
) -> ArticlePage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    before_published_at, before_id = (None, None)
    if cursor:
        before_published_at, before_id = decode_cursor(cursor)

    # Fetch one extra row to learn whether another page exists without a count.
    rows = await repo.list_articles(
        session,
        languages=parse_languages(languages),
        limit=page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
        topic_id=topic,
        country=country,
    )

    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = (
        encode_cursor(items[-1].published_at, items[-1].id) if has_more and items else None
    )
    return ArticlePage(items=items, next_cursor=next_cursor)


async def get_article(session: AsyncSession, article_id: int) -> repo.ArticleRow:
    article = await repo.get_article(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    return article


@dataclass(frozen=True, slots=True)
class StoryDetail:
    cluster: StoryCluster
    articles: list[repo.ArticleRow]
    # Which languages this story is being reported in, and by how many
    # distinct outlets each. Cross-lingual clustering is what makes this
    # answerable at all - it is the same event in three languages, not three
    # events (ADR 0005).
    coverage: list[repo.LanguageCoverage]


async def get_story(session: AsyncSession, story_id: int) -> StoryDetail:
    cluster = await repo.get_story_cluster(session, story_id)
    if cluster is None:
        raise NotFoundError(f"No story with id {story_id}.")
    articles = await repo.list_articles_in_cluster(session, story_id)
    coverage = (await repo.language_coverage(session, [story_id])).get(story_id, [])
    return StoryDetail(cluster=cluster, articles=articles, coverage=coverage)


@dataclass(frozen=True, slots=True)
class Blindspot:
    """A story with real coverage, none of it in a language the reader reads."""

    cluster: StoryCluster
    coverage: list[repo.LanguageCoverage]


# A story carried by only one outlet is not a blindspot, it is one outlet's
# story. Two is the smallest number that means "this is being reported".
BLINDSPOT_MIN_SOURCES = 2
BLINDSPOT_WINDOW = timedelta(days=3)


async def get_blindspots(
    session: AsyncSession, *, languages: list[str], limit: int = 6
) -> list[Blindspot]:
    """Recent stories nobody is covering in the reader's languages.

    Deliberately not a recommendation: it is a factual statement about where
    coverage exists. That is also why it is honest in a way a partisan
    blindspot feed is not - it counts articles rather than judging outlets.
    """
    clusters = await repo.list_blindspot_clusters(
        session,
        languages=languages,
        since=datetime.now(UTC) - BLINDSPOT_WINDOW,
        min_sources=BLINDSPOT_MIN_SOURCES,
        limit=limit,
    )
    coverage = await repo.language_coverage(session, [cluster.id for cluster in clusters])
    return [
        Blindspot(cluster=cluster, coverage=coverage.get(cluster.id, [])) for cluster in clusters
    ]


# Long enough that a quiet overnight window still has something in it, short
# enough that "trending" means now rather than this week.
TRENDING_WINDOW = timedelta(hours=24)


async def get_trending(
    session: AsyncSession, *, languages: list[str] | None, limit: int = 6
) -> list[repo.ArticleRow]:
    return await repo.list_trending(
        session,
        languages=languages,
        since=datetime.now(UTC) - TRENDING_WINDOW,
        limit=limit,
    )


async def list_editions(session: AsyncSession, *, languages: list[str] | None) -> list[Edition]:
    return await repo.list_editions(session, languages=languages)


# A discovery list for onboarding, not a directory - bounded so a reader
# meets a handful of recognisable names, not the entire source table.
SOURCE_DISCOVERY_LIMIT = 12


async def list_sources_for_language(session: AsyncSession, *, language: str) -> list[Source]:
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")
    return await repo.list_sources_for_language(
        session, language=code, limit=SOURCE_DISCOVERY_LIMIT
    )
