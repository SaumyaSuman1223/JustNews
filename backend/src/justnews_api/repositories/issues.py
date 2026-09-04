"""Reads over the frozen issue tables.

Everything here is a keyed read of rows a composer wrote hours ago (ADR 0012),
which is the whole point of Aquila being a publication rather than a feed: no
ranking, no candidate window, no per-reader work. The most expensive query in
this module is one join.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from justnews_api.repositories.content import ArticleRow
from justnews_core.models import Article, Issue, IssuePage, IssueSlot, Source, Topic


@dataclass(frozen=True, slots=True)
class PageSummary:
    """One entry in the contents - enough to render the page rail, no articles."""

    page_no: int
    topic_id: str | None
    topic: Topic | None


@dataclass(frozen=True, slots=True)
class IssueSummary:
    issue: Issue
    pages: list[PageSummary]


@dataclass(frozen=True, slots=True)
class SlotRow:
    position: int
    role: str
    article: ArticleRow


@dataclass(frozen=True, slots=True)
class PageContent:
    page_no: int
    topic_id: str | None
    topic: Topic | None
    slots: list[SlotRow]


async def _summarise(session: AsyncSession, issue: Issue) -> IssueSummary:
    rows = (
        await session.execute(
            select(IssuePage, Topic)
            .outerjoin(Topic, Topic.id == IssuePage.topic_id)
            .where(IssuePage.issue_id == issue.id)
            .order_by(IssuePage.page_no)
            # The section name is the topic's label in the reader's locale, so
            # the labels come along rather than costing a query per page.
            .options(selectinload(Topic.labels))
        )
    ).all()
    return IssueSummary(
        issue=issue,
        pages=[
            PageSummary(page_no=page.page_no, topic_id=page.topic_id, topic=topic)
            for page, topic in rows
        ],
    )


async def latest_issue(session: AsyncSession, *, locale: str) -> IssueSummary | None:
    """The most recently published issue for a locale, with its contents."""
    issue = await session.scalar(
        select(Issue).where(Issue.locale == locale).order_by(Issue.published_at.desc()).limit(1)
    )
    if issue is None:
        return None
    return await _summarise(session, issue)


async def issue_by_id(session: AsyncSession, issue_id: int) -> IssueSummary | None:
    issue = await session.get(Issue, issue_id)
    if issue is None:
        return None
    return await _summarise(session, issue)


async def issues_on(session: AsyncSession, *, locale: str, on: date) -> list[Issue]:
    """Every edition published for a locale on one day, earliest first.

    Backs the edition selector: a reader who opens Aquila at 23:00 should be
    able to reach that morning's paper, not just the current one.
    """
    return list(
        (
            await session.scalars(
                select(Issue)
                .where(Issue.locale == locale, Issue.published_on == on)
                .order_by(Issue.published_at)
            )
        ).all()
    )


async def page_content(session: AsyncSession, *, issue_id: int, page_no: int) -> PageContent | None:
    page_row = (
        await session.execute(
            select(IssuePage, Topic)
            .outerjoin(Topic, Topic.id == IssuePage.topic_id)
            .where(IssuePage.issue_id == issue_id, IssuePage.page_no == page_no)
            .options(selectinload(Topic.labels))
        )
    ).first()
    if page_row is None:
        return None
    page, topic = page_row

    rows = (
        await session.execute(
            select(IssueSlot, Article, Source)
            .join(Article, Article.id == IssueSlot.article_id)
            .join(Source, Source.id == Article.source_id)
            # A takedown hides an article everywhere, including from a paper
            # that was composed before it was pulled. The slot stays in the
            # table - the issue is immutable - but the page renders without it.
            .where(IssueSlot.page_id == page.id, Article.removed_at.is_(None))
            .order_by(IssueSlot.position)
        )
    ).all()

    return PageContent(
        page_no=page.page_no,
        topic_id=page.topic_id,
        topic=topic,
        slots=[
            SlotRow(
                position=slot.position,
                role=slot.role,
                article=ArticleRow.from_pair(article, source),
            )
            for slot, article, source in rows
        ],
    )
