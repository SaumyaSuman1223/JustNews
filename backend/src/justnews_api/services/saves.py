"""Bookmarks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import saves as repo
from justnews_api.services.content import MAX_PAGE_SIZE
from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import NotFoundError, ValidationError


@dataclass(frozen=True, slots=True)
class SavedArticle:
    article: content_repo.ArticleRow
    saved_at: datetime


@dataclass(frozen=True, slots=True)
class SavePage:
    items: list[SavedArticle]
    next_cursor: str | None


async def save_article(session: AsyncSession, user_id: UUID, article_id: int) -> SavedArticle:
    article = await content_repo.get_article(session, article_id)
    if article is None:
        raise NotFoundError(f"No article with id {article_id}.")
    row = await repo.create_save(session, user_id, article_id)
    return SavedArticle(article=article, saved_at=row.created_at)


async def unsave_article(session: AsyncSession, user_id: UUID, article_id: int) -> None:
    if not await repo.delete_save(session, user_id, article_id):
        raise NotFoundError(f"No save for article {article_id}.")


async def list_saved(
    session: AsyncSession, user_id: UUID, *, cursor: str | None, page_size: int
) -> SavePage:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    before_created_at, before_id = (None, None)
    if cursor:
        before_created_at, before_id = decode_cursor(cursor)

    rows = await repo.list_saves(
        session,
        user_id,
        limit=page_size + 1,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    has_more = len(rows) > page_size
    page_rows = rows[:page_size]

    articles = await content_repo.get_articles_by_id(session, [row.article_id for row in page_rows])
    items = [
        SavedArticle(article=articles[row.article_id], saved_at=row.created_at)
        for row in page_rows
        if row.article_id in articles  # skip a save whose article has since been pruned
    ]
    next_cursor = (
        encode_cursor(page_rows[-1].created_at, page_rows[-1].id)
        if has_more and page_rows
        else None
    )
    return SavePage(items=items, next_cursor=next_cursor)
