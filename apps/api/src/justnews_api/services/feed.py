"""The personalised feed surface.

Every reader is deterministically bucketed into one of two serving policies -
"heuristic_v1" (Stage 5's ranker) or "chronological" (the Stage 2 fallback,
now doubling as the Stage 5 A/B control) - and stays in that bucket for as
long as their user id is stable, which is what makes the comparison a valid
experiment rather than noise. `/v1/admin/analytics/overview` reports CTR by
policy; that is the "experiment console" result Stage 5's done-when
criterion asks for - and it is only a real result because every item on the
feed carries its own impression id back to the client, so a later click can
be attributed to the exact impression (and therefore policy) that served it,
rather than guessed at from a surface and a timestamp.

A deterministic policy still has a propensity: every item shown had
probability 1 of being shown given the request - which policy a reader is
in is bucketed once per user, not re-rolled per request, and the ranking
itself has no randomness in it. Logging propensity now is what makes Stage
6's offline evaluation unbiased later; the column cannot be back-filled onto
impressions this system already served.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import follows as follows_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import ranking as ranking_repo
from justnews_api.repositories import users as users_repo
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services import ranking
from justnews_api.services.content import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import (
    decode_cursor,
    decode_rank_cursor,
    encode_cursor,
    encode_rank_cursor,
)
from justnews_core.errors import ValidationError

PROPENSITY = 1.0

# How much of the recent corpus the ranker considers per feed load. Large
# enough for MMR to have real material to diversify over and for several
# pages of pagination; small enough to score and diversify well inside a
# request (see services.ranking - both passes are near-linear in this size).
CANDIDATE_POOL_SIZE = 200
SEEN_WINDOW = timedelta(days=14)
POPULARITY_WINDOW = timedelta(days=7)

HEURISTIC_POLICY = "heuristic_v1"
CHRONOLOGICAL_POLICY = "chronological"


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    """Everything any ranking policy is allowed to ask for.

    One shape for every policy so the serving path never branches on which one
    is in play. A policy that does not need `user_id` simply ignores it - which
    is what makes adding a new ranker a matter of writing a function and
    registering it, rather than editing get_feed_page.
    """

    user_id: UUID
    languages: list[str] | None
    excluded: set[int]
    cursor: str | None
    page_size: int


RankingPolicy = Callable[[AsyncSession, PolicyRequest], Awaitable["_UnloggedPage"]]


def assign_policy(user_id: UUID) -> str:
    """Stable per reader: the same user id always lands in the same bucket,
    which is what makes this an A/B test rather than a coin flip on every
    request. Not stored anywhere - recomputed identically each time from the
    one thing that never changes, the user's own id.

    Buckets over EXPERIMENT_POLICIES, not POLICIES. Registering a ranker and
    putting it in front of readers are deliberately separate decisions: a new
    model gets implemented and tested first, and only joins the split when
    someone decides it should. Adding one to EXPERIMENT_POLICIES does
    re-bucket every reader, which ends the running experiment - that is
    inherent to changing the split, not something to paper over.
    """
    digest = hashlib.sha256(str(user_id).encode("ascii")).digest()
    return EXPERIMENT_POLICIES[digest[0] % len(EXPERIMENT_POLICIES)]


@dataclass(frozen=True, slots=True)
class FeedItem:
    article: content_repo.ArticleRow
    impression_id: int


@dataclass(frozen=True, slots=True)
class FeedPage:
    items: list[FeedItem]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class _UnloggedPage:
    articles: list[content_repo.ArticleRow]
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

    excluded = await interactions_repo.excluded_article_ids(session, user_id)
    policy = assign_policy(user_id)

    unlogged = await POLICIES[policy](
        session,
        PolicyRequest(
            user_id=user_id,
            languages=requested_languages,
            excluded=excluded,
            cursor=cursor,
            page_size=page_size,
        ),
    )

    if not unlogged.articles:
        return FeedPage(items=[], next_cursor=unlogged.next_cursor)

    impression_ids = await interactions_repo.log_impressions(
        session,
        user_id=user_id,
        session_id=session_id,
        surface="feed",
        locale=locale,
        ranking_policy=policy,
        items=[
            ImpressionToLog(article_id=row.id, position=position, propensity=PROPENSITY)
            for position, row in enumerate(unlogged.articles)
        ],
    )
    items = [
        FeedItem(article=article, impression_id=impression_id)
        for article, impression_id in zip(unlogged.articles, impression_ids, strict=True)
    ]
    return FeedPage(items=items, next_cursor=unlogged.next_cursor)


async def _get_chronological_page(session: AsyncSession, request: PolicyRequest) -> _UnloggedPage:
    before_published_at, before_id = (None, None)
    if request.cursor:
        before_published_at, before_id = decode_cursor(request.cursor)

    rows = await content_repo.list_articles(
        session,
        languages=request.languages,
        limit=request.page_size + 1,
        before_published_at=before_published_at,
        before_id=before_id,
        exclude_article_ids=request.excluded,
    )
    has_more = len(rows) > request.page_size
    articles = rows[: request.page_size]
    next_cursor = (
        encode_cursor(articles[-1].published_at, articles[-1].id) if has_more and articles else None
    )
    return _UnloggedPage(articles=articles, next_cursor=next_cursor)


async def _get_heuristic_page(session: AsyncSession, request: PolicyRequest) -> _UnloggedPage:
    languages, page_size = request.languages, request.page_size
    now = datetime.now(UTC)
    if request.cursor:
        window_upper_bound, offset = decode_rank_cursor(request.cursor)
    else:
        window_upper_bound, offset = now, 0

    candidates = await content_repo.list_articles_window(
        session,
        languages=languages,
        upper_bound=window_upper_bound,
        exclude_article_ids=request.excluded,
        limit=CANDIDATE_POOL_SIZE,
    )
    candidate_ids = [row.id for row in candidates]

    # Sequential, not gathered: these all share one AsyncSession, which
    # SQLAlchemy does not support issuing concurrent queries on.
    topic_ids_by_article = await ranking_repo.topic_ids_by_article(session, candidate_ids)
    click_counts = await ranking_repo.recent_click_counts(
        session, candidate_ids, since=now - POPULARITY_WINDOW
    )
    followed_topic_ids = await follows_repo.list_followed_topic_ids(session, request.user_id)
    seen_ids = await ranking_repo.seen_article_ids(
        session, request.user_id, since=now - SEEN_WINDOW
    )

    scored = ranking.score_candidates(
        candidates,
        topic_ids_by_article=topic_ids_by_article,
        click_counts=click_counts,
        followed_topic_ids=followed_topic_ids,
        seen_article_ids=seen_ids,
        preferred_languages=languages or [],
        now=now,
    )
    ranked = ranking.diversify(ranking.dedupe_story_clusters(scored))

    articles = ranked[offset : offset + page_size]
    has_more = len(ranked) > offset + page_size
    next_cursor = encode_rank_cursor(window_upper_bound, offset + page_size) if has_more else None
    return _UnloggedPage(articles=articles, next_cursor=next_cursor)


# --- the ranking registry -------------------------------------------------
#
# The seam this whole module is shaped around. Adding a ranker - Stage 6's
# FINDING model, or anything after it - means writing one function with the
# RankingPolicy signature and adding one entry here. get_feed_page does not
# change, impression logging does not change, and the A/B attribution built in
# Stage 5 keeps working because `ranking_policy` is just this key.
#
# Defined at the bottom because the values are the functions above; the names
# are resolved when a request is served, not at import.
POLICIES: dict[str, RankingPolicy] = {
    HEURISTIC_POLICY: _get_heuristic_page,
    CHRONOLOGICAL_POLICY: _get_chronological_page,
}

# Which of them are currently in front of readers. Deliberately a separate
# list: a new ranker should be registered, exercised and measured offline
# before it is added here, and adding it re-buckets every reader.
EXPERIMENT_POLICIES: tuple[str, ...] = (HEURISTIC_POLICY, CHRONOLOGICAL_POLICY)
