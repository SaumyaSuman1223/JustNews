"""The personalised feed surface.

No ranker exists yet - that is Stage 6. Until then this degrades to
reverse-chronological, filtered to the reader's languages and with anything
they marked not interested in excluded. A deterministic policy still has a
propensity: every item shown had probability 1 of being shown given the
request, and logging that now is what makes Stage 6's offline evaluation
unbiased later - the column cannot be back-filled onto impressions this
system already served.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import users as users_repo
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import ValidationError

CHRONOLOGICAL_PROPENSITY = 1.0


@dataclass(frozen=True, slots=True)
class FeedPage:
    items: list[content_repo.ArticleRow]
    next_cursor: str | None


async def get_feed_page(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: str,
    locale: str,
    languages: str | None,
    cursor: str | None,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> FeedPage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    requested_languages = parse_languages(languages)
    if requested_languages is None:
        profile = await users_repo.get_profile(session, user_id)
        if profile is not None and profile.preferred_languages:
            requested_languages = list(profile.preferred_languages)

    before_published_at, before_id = (None, None)
    if cursor:
        before_published_at, before_id = decode_cursor(cursor)

    excluded = await interactions_repo.excluded_article_ids(session, user_id)

    rows = await content_repo.list_articles(
        session,
        languages=requested_languages,
        limit=page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
        exclude_article_ids=excluded,
    )

    has_more = len(rows) > page_size
    items = rows[:page_size]

    if items:
        await interactions_repo.log_impressions(
            session,
            user_id=user_id,
            session_id=session_id,
            surface="feed",
            locale=locale,
            items=[
                ImpressionToLog(
                    article_id=row.id, position=position, propensity=CHRONOLOGICAL_PROPENSITY
                )
                for position, row in enumerate(items)
            ],
        )

    next_cursor = (
        encode_cursor(items[-1].published_at, items[-1].id) if has_more and items else None
    )
    return FeedPage(items=items, next_cursor=next_cursor)
