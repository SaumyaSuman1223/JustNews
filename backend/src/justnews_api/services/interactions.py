"""Interaction reporting: what a reader did about something they were shown.

Distinct from saves and follows - those are declarative state the reader
controls directly. This is an append-only log of events a client reports
after the fact, which is what the Stage 6 ranker eventually trains on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import interactions as repo
from justnews_api.services.content import MAX_PAGE_SIZE
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import NotFoundError, ValidationError

VALID_SURFACES = ("feed", "explore", "search", "topic")


def _validate_surface(surface: str) -> None:
    if surface not in VALID_SURFACES:
        raise ValidationError(f"surface must be one of {VALID_SURFACES}.")


async def report_click(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: str,
    article_id: int,
    surface: str,
    position: int | None,
    impression_id: int | None,
) -> None:
    _validate_surface(surface)
    article = await content_repo.get_article(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    await repo.record_event(
        session,
        user_id=user_id,
        session_id=session_id,
        article_id=article_id,
        event_type="click",
        surface=surface,
        locale=article.language,
        impression_id=impression_id,
        position=position,
    )


async def report_not_interested(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: str,
    article_id: int,
    surface: str,
) -> None:
    _validate_surface(surface)
    article = await content_repo.get_article(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    await repo.record_event(
        session,
        user_id=user_id,
        session_id=session_id,
        article_id=article_id,
        event_type="not_interested",
        surface=surface,
        locale=article.language,
    )


@dataclass(frozen=True, slots=True)
class HistoryItem:
    article: content_repo.ArticleRow
    viewed_at: datetime


@dataclass(frozen=True, slots=True)
class HistoryPage:
    items: list[HistoryItem]
    next_cursor: str | None


async def list_history(
    session: AsyncSession, user_id: UUID, *, cursor: str | None, page_size: int
) -> HistoryPage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    before_viewed_at, before_id = (None, None)
    if cursor:
        before_viewed_at, before_id = decode_cursor(cursor)

    rows = await repo.list_history(
        session,
        user_id,
        limit=page_size + 1,
        before_viewed_at=before_viewed_at,
        before_id=before_id,
    )
    has_more = len(rows) > page_size
    page_rows = rows[:page_size]

    articles = await content_repo.get_articles_by_id(session, [row.article_id for row in page_rows])
    items = [
        HistoryItem(article=articles[row.article_id], viewed_at=row.viewed_at)
        for row in page_rows
        if row.article_id in articles
    ]
    next_cursor = (
        encode_cursor(page_rows[-1].viewed_at, page_rows[-1].id) if has_more and page_rows else None
    )
    return HistoryPage(items=items, next_cursor=next_cursor)
