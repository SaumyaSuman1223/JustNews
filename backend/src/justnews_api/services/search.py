from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as repo
from justnews_api.services.content import MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import ValidationError

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: list[repo.ArticleRow]
    next_cursor: str | None
    #: How many articles match in total. ``None`` past the first page - see
    #: below; a client already has it from the page it started on.
    total: int | None


async def search(
    session: AsyncSession,
    *,
    query_text: str,
    languages: str | None,
    topic_id: str | None,
    source_id: int | None,
    cursor: str | None,
    page_size: int,
) -> SearchPage:
    query_text = query_text.strip()
    if not MIN_QUERY_LENGTH <= len(query_text) <= MAX_QUERY_LENGTH:
        raise ValidationError(
            f"q must be between {MIN_QUERY_LENGTH} and {MAX_QUERY_LENGTH} characters."
        )
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    before_published_at, before_id = (None, None)
    if cursor:
        before_published_at, before_id = decode_cursor(cursor)

    # Audit §28 wants the results heading to say how many there are. A
    # keyset feed cannot know that from the page it just returned, so it is a
    # second query - run only when there is no cursor, because a count over
    # the same predicate returns the same number on every page and paying for
    # it again on page four buys nothing.
    total = (
        None
        if cursor
        else await repo.count_search_articles(
            session,
            query_text=query_text,
            languages=parse_languages(languages),
            topic_id=topic_id,
            source_id=source_id,
        )
    )

    rows = await repo.search_articles(
        session,
        query_text=query_text,
        languages=parse_languages(languages),
        topic_id=topic_id,
        source_id=source_id,
        limit=page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
    )
    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = (
        encode_cursor(items[-1].published_at, items[-1].id) if has_more and items else None
    )
    return SearchPage(items=items, next_cursor=next_cursor, total=total)
