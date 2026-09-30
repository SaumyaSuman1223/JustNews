"""Discover's views for every reader (ADR 0015): For You, Top and a topic, one
call per page, whoever is reading.

An invited reader's For You is the feed experiment - `services.feed`, where
the A/B split and its chronological holdout live. Everything else is ranker
v2 directly: a signed-in reader personalised from their account, a
signed-out one from the reads this device sent (and nothing stored about
them beyond what analytics consent allows).

A page is logged - impressions with the probability each placement had -
only with analytics consent. Without it the order is the deterministic
argmax, the same for every such reader, which is what lets the router cache
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import users as users_repo
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services import feed as feed_service
from justnews_api.services import recommend
from justnews_api.services.content import MAX_PAGE_SIZE, parse_languages
from justnews_api.services.cursor import MAX_CURSOR_HISTORY
from justnews_api.services.scoring import RankReason
from justnews_core.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DiscoverItem:
    article: content_repo.ArticleRow
    impression_id: int | None
    reason: RankReason | None
    position: int


@dataclass(frozen=True, slots=True)
class DiscoverPage:
    items: list[DiscoverItem]
    next_cursor: str | None


def parse_history(raw: str | None) -> list[int]:
    """``"912,877,640"`` - this device's recent reads, newest first - into ids.
    Capped rather than refused past the limit: it is a hint, and the oldest
    reads are the least useful ones."""
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ValidationError(f"Not an article id: {part!r}")
        value = int(part)
        if value not in ids:
            ids.append(value)
    return ids[:MAX_CURSOR_HISTORY]


async def get_page(
    session: AsyncSession,
    *,
    view: recommend.View,
    topic: str | None,
    interests: list[str],
    history: list[int],
    languages: str | None,
    locale: str,
    cursor: str | None,
    page_size: int,
    user_id: UUID | None,
    session_id: str | None,
    log: bool,
) -> DiscoverPage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")
    if view == "topic" and not topic:
        raise ValidationError("The topic view needs a topic.")

    profile = await users_repo.get_profile(session, user_id) if user_id is not None else None
    requested = parse_languages(languages)
    if requested is None:
        requested = (
            list(profile.preferred_languages)
            if profile is not None and profile.preferred_languages
            else [locale]
        )
    invited = profile is not None and (
        profile.role == "admin" or profile.invite_redeemed_at is not None
    )

    if view == "for_you" and user_id is not None and invited:
        feed = await feed_service.get_feed_page(
            session,
            user_id=user_id,
            session_id=session_id or "",
            locale=locale,
            languages=",".join(requested),
            cursor=cursor,
            page_size=page_size,
            log_impressions=log and session_id is not None,
        )
        return DiscoverPage(
            items=[
                DiscoverItem(
                    article=item.article,
                    impression_id=item.impression_id,
                    reason=item.reason,
                    position=item.position,
                )
                for item in feed.items
            ],
            next_cursor=feed.next_cursor,
        )

    ranked = await recommend.rank(
        session,
        recommend.RankRequest(
            view=view,
            languages=requested,
            topic_ids=[topic] if topic else None,
            interests=interests,
            user_id=user_id,
            session_id=session_id if log else None,
            history=history if user_id is None else [],
            cursor=cursor,
            page_size=page_size,
            stochastic=log,
        ),
    )
    impression_ids: list[int | None] = [None] * len(ranked.items)
    if log and session_id is not None and ranked.items:
        impression_ids = list(
            await interactions_repo.log_impressions(
                session,
                user_id=user_id,
                session_id=session_id,
                served_at=datetime.now(UTC),
                surface=recommend.surface_for(view),
                locale=locale,
                ranking_policy=recommend.POLICY,
                items=[
                    ImpressionToLog(
                        article_id=item.article.id,
                        position=item.position,
                        propensity=item.propensity,
                    )
                    for item in ranked.items
                ],
            )
        )
    return DiscoverPage(
        items=[
            DiscoverItem(
                article=item.article,
                impression_id=impression_id,
                reason=item.reason,
                position=item.position,
            )
            for item, impression_id in zip(ranked.items, impression_ids, strict=True)
        ],
        next_cursor=ranked.next_cursor,
    )
