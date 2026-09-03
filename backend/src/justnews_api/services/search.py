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


async def search(
    session: AsyncSession,
    *,
    query_text: str,
    languages: str | None,
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

    rows = await repo.search_articles(
        session,
        query_text=query_text,
        languages=parse_languages(languages),
        limit=page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
    )
    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = (
        encode_cursor(items[-1].published_at, items[-1].id) if has_more and items else None
    )
    return SearchPage(items=items, next_cursor=next_cursor)
