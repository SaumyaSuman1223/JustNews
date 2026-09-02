"""The explore surface: latest news, ranked, for everyone.

Deliberately *not* personalised. Explore is where a reader with no history
starts and where a signed-out visitor lands, so it must produce the same page
for everyone - which is also what makes it a usable control to measure the
personalised feed against later.

It is still ranked rather than a raw reverse-chronological dump. The same
scoring and diversity code the Stage 5 feed uses runs here, with every
personalisation signal fed in empty: no followed topics, no click history, no
seen-article penalty. What survives is recency, source trust and language
match, plus story-cluster dedup and MMR diversity - so the page never opens
with eight versions of one wire story, which is the failure a plain "newest
first" list has on a corpus built from hundreds of feeds.

Reusing services.ranking rather than writing a second ranker is the point:
one implementation of "how a page of articles is composed", two ways of
scoring it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import ranking as ranking_repo
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services import ranking
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import decode_rank_cursor, encode_rank_cursor
from justnews_api.services.feed import CANDIDATE_POOL_SIZE, PROPENSITY, FeedItem, FeedPage
from justnews_core.errors import ValidationError

# Named like a ranking policy because that is what it is - it lands in
# `impressions.ranking_policy` beside the feed's policies, so explore CTR can
# be compared against them in the same admin view rather than a separate one.
EXPLORE_POLICY = "latest_v1"


@dataclass(frozen=True, slots=True)
class _Unlogged:
    articles: list[content_repo.ArticleRow]
    next_cursor: str | None


async def get_explore_page(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str,
    locale: str,
    languages: str | None,
    cursor: str | None,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> FeedPage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    requested_languages = parse_languages(languages)
    excluded = (
        await interactions_repo.excluded_article_ids(session, user_id)
        if user_id is not None
        else set()
    )

    unlogged = await _rank(
        session,
        languages=requested_languages,
        excluded=excluded,
        cursor=cursor,
        page_size=page_size,
    )
    if not unlogged.articles:
        return FeedPage(items=[], next_cursor=unlogged.next_cursor)

    impression_ids = await interactions_repo.log_impressions(
        session,
        user_id=user_id,
        session_id=session_id,
        surface="explore",
        locale=locale,
        ranking_policy=EXPLORE_POLICY,
        items=[
            ImpressionToLog(article_id=row.id, position=position, propensity=PROPENSITY)
            for position, row in enumerate(unlogged.articles)
        ],
    )
    return FeedPage(
        items=[
            FeedItem(article=article, impression_id=impression_id)
            for article, impression_id in zip(unlogged.articles, impression_ids, strict=True)
        ],
        next_cursor=unlogged.next_cursor,
    )


async def _rank(
    session: AsyncSession,
    *,
    languages: list[str] | None,
    excluded: set[int],
    cursor: str | None,
    page_size: int,
) -> _Unlogged:
    now = datetime.now(UTC)
    window_upper_bound, offset = decode_rank_cursor(cursor) if cursor else (now, 0)

    candidates = await content_repo.list_articles_window(
        session,
        languages=languages,
        upper_bound=window_upper_bound,
        exclude_article_ids=excluded,
        limit=CANDIDATE_POOL_SIZE,
    )
    # Topics are still loaded, but only to feed MMR: two articles sharing a
    # topic are redundant with each other regardless of whether this reader
    # likes that topic. Diversity is not personalisation.
    topic_ids_by_article = await ranking_repo.topic_ids_by_article(
        session, [row.id for row in candidates]
    )

    scored = ranking.score_candidates(
        candidates,
        topic_ids_by_article=topic_ids_by_article,
        click_counts={},
        followed_topic_ids=set(),
        seen_article_ids=set(),
        preferred_languages=languages or [],
        now=now,
    )
    ranked = ranking.diversify(ranking.dedupe_story_clusters(scored))

    has_more = len(ranked) > offset + page_size
    return _Unlogged(
        articles=ranked[offset : offset + page_size],
        next_cursor=encode_rank_cursor(window_upper_bound, offset + page_size)
        if has_more
        else None,
    )
