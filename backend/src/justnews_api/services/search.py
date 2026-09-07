from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as repo
from justnews_api.repositories import topics as topics_repo
from justnews_api.services.content import MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_api.services.topics import label_for
from justnews_core.errors import ValidationError

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200

#: §21's date filter, as named ranges rather than a raw date picker - the
#: honest options for a corpus that only goes back a few weeks, and simpler
#: for a reader than choosing two calendar dates.
DATE_WINDOWS: dict[str, timedelta] = {
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}

#: How many topic/source matches to show per group - §21 wants these as a
#: pointer into browse, not a second paginated list living beside the
#: articles.
MAX_GROUP_MATCHES = 5


def _published_after(date_window: str | None) -> datetime | None:
    if not date_window:
        return None
    delta = DATE_WINDOWS.get(date_window)
    if delta is None:
        raise ValidationError(f"date must be one of {sorted(DATE_WINDOWS)}.")
    return datetime.now(UTC) - delta


@dataclass(frozen=True, slots=True)
class TopicMatch:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class SourceMatch:
    id: int
    name: str
    homepage_url: str


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: list[repo.ArticleRow]
    next_cursor: str | None
    #: How many articles match in total. ``None`` past the first page - see
    #: below; a client already has it from the page it started on.
    total: int | None
    #: Topics and sources whose *name* matches the query, not just articles
    #: that mention it - §21's result grouping. ``None`` past the first page,
    #: same reasoning as ``total``: the predicate does not change with the
    #: cursor, so recomputing it on every page would return the same rows for
    #: the cost of two more queries.
    matched_topics: list[TopicMatch] | None
    matched_sources: list[SourceMatch] | None


async def search(
    session: AsyncSession,
    *,
    query_text: str,
    languages: str | None,
    topic_id: str | None,
    source_id: int | None,
    date_window: str | None,
    interface_language: str,
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
    published_after = _published_after(date_window)

    before_published_at, before_id = (None, None)
    if cursor:
        before_published_at, before_id = decode_cursor(cursor)

    # Audit §28 wants the results heading to say how many there are. A
    # keyset feed cannot know that from the page it just returned, so it is a
    # second query - run only when there is no cursor, because a count over
    # the same predicate returns the same number on every page and paying for
    # it again on page four buys nothing. The topic/source groups are the
    # same idea: a fixed answer for the query, so computed once rather than
    # re-run behind every page of articles.
    total: int | None = None
    matched_topics: list[TopicMatch] | None = None
    matched_sources: list[SourceMatch] | None = None
    if not cursor:
        total = await repo.count_search_articles(
            session,
            query_text=query_text,
            languages=parse_languages(languages),
            topic_id=topic_id,
            source_id=source_id,
            published_after=published_after,
            published_before=None,
        )
        topic_rows = await topics_repo.search_topics(
            session, query=query_text, language=interface_language, limit=MAX_GROUP_MATCHES
        )
        matched_topics = [
            TopicMatch(id=topic.id, label=label_for(topic, interface_language))
            for topic in topic_rows
        ]
        source_rows = await repo.search_sources(session, query=query_text, limit=MAX_GROUP_MATCHES)
        matched_sources = [
            SourceMatch(id=source.id, name=source.name, homepage_url=source.homepage_url)
            for source in source_rows
        ]

    rows = await repo.search_articles(
        session,
        query_text=query_text,
        languages=parse_languages(languages),
        topic_id=topic_id,
        source_id=source_id,
        published_after=published_after,
        published_before=None,
        limit=page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
    )
    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = (
        encode_cursor(items[-1].published_at, items[-1].id) if has_more and items else None
    )
    return SearchPage(
        items=items,
        next_cursor=next_cursor,
        total=total,
        matched_topics=matched_topics,
        matched_sources=matched_sources,
    )
