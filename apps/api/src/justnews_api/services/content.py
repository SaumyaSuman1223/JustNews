"""Public, unauthenticated content service.

Anonymous browsing over the corpus - no ranking, no personalisation. That is
``services/feed.py``, which requires a signed-in reader.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as repo
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import NotFoundError, ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import StoryCluster

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


async def get_story(session: AsyncSession, story_id: int) -> StoryDetail:
    cluster = await repo.get_story_cluster(session, story_id)
    if cluster is None:
        raise NotFoundError(f"No story with id {story_id}.")
    articles = await repo.list_articles_in_cluster(session, story_id)
    return StoryDetail(cluster=cluster, articles=articles)
