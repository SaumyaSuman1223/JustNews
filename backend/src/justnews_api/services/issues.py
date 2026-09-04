"""The Aquila Tribune, served.

Serving is deliberately dull: an issue was composed hours ago and frozen
(ADR 0012), so this reads it, looks up section names in the reader's locale,
and logs what it showed. There is no ranking here and there must never be -
the moment Aquila starts deciding anything per-request it stops being a
publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import flags as flags_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import issues as issues_repo
from justnews_api.repositories.content import ArticleRow
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services.topics import label_for
from justnews_core.errors import NotFoundError
from justnews_core.models import Issue

AQUILA_FLAG = "aquila"
AQUILA_SURFACE = "aquila"
AQUILA_POLICY = "aquila_issue_v1"

# Aquila's propensity is genuinely 1.0, and that is not the placeholder it
# looks like. The exploration deck samples, so its slots carry a real
# fractional probability; a composed page does not - given the issue, the
# policy showed that article in that position with certainty. Logging a
# fraction here would misdescribe what happened, and Stage 6's offline
# evaluation reads this column literally.
PROPENSITY = 1.0


@dataclass(frozen=True, slots=True)
class PageSection:
    page_no: int
    topic_id: str | None
    title: str | None


@dataclass(frozen=True, slots=True)
class IssueView:
    issue: Issue
    sections: list[PageSection]


@dataclass(frozen=True, slots=True)
class SlotView:
    position: int
    role: str
    article: ArticleRow
    impression_id: int | None


@dataclass(frozen=True, slots=True)
class PageView:
    page_no: int
    topic_id: str | None
    title: str | None
    slots: list[SlotView]


def _sections(summary: issues_repo.IssueSummary, locale: str) -> list[PageSection]:
    return [
        PageSection(
            page_no=page.page_no,
            topic_id=page.topic_id,
            # The front page has no topic and therefore no section name; the
            # client supplies its own masthead line for page 1. Section pages
            # take the IPTC label in the reader's locale (ADR 0006) rather
            # than a section string stored at compose time, which would have
            # frozen one language into the issue.
            title=label_for(page.topic, locale) if page.topic is not None else None,
        )
        for page in summary.pages
    ]


async def get_latest_issue(session: AsyncSession, *, locale: str) -> IssueView | None:
    """The current paper, or None when there is not one.

    None is an ordinary outcome, not an error: before the first edition of a
    locale, after a thin-corpus skip, or with the flag off. The client renders
    its "no issue yet" state, which is a real state a publication has.
    """
    if not await flags_repo.is_enabled(session, AQUILA_FLAG):
        return None
    summary = await issues_repo.latest_issue(session, locale=locale)
    if summary is None:
        return None
    return IssueView(issue=summary.issue, sections=_sections(summary, locale))


async def get_issue(session: AsyncSession, *, issue_id: int, locale: str) -> IssueView:
    if not await flags_repo.is_enabled(session, AQUILA_FLAG):
        raise NotFoundError("No issue.")
    summary = await issues_repo.issue_by_id(session, issue_id)
    if summary is None:
        raise NotFoundError("No issue.")
    return IssueView(issue=summary.issue, sections=_sections(summary, locale))


async def list_editions(session: AsyncSession, *, locale: str, on: date | None) -> list[Issue]:
    """The day's editions, for the selector.

    Defaults to the day of the latest issue rather than to today: at 02:00 a
    reader is looking at last night's evening edition, and offering them an
    empty list for a day that has not published yet is worse than offering
    the three editions the paper they are holding belongs to.
    """
    if not await flags_repo.is_enabled(session, AQUILA_FLAG):
        return []
    if on is None:
        summary = await issues_repo.latest_issue(session, locale=locale)
        if summary is None:
            return []
        on = summary.issue.published_on
    return await issues_repo.issues_on(session, locale=locale, on=on)


async def get_page(
    session: AsyncSession,
    *,
    issue_id: int,
    page_no: int,
    locale: str,
    user_id: UUID | None,
    session_id: str,
    log_impressions: bool = True,
) -> PageView:
    if not await flags_repo.is_enabled(session, AQUILA_FLAG):
        raise NotFoundError("No issue.")

    content = await issues_repo.page_content(session, issue_id=issue_id, page_no=page_no)
    if content is None:
        raise NotFoundError("No such page.")

    impression_ids: list[int | None] = [None] * len(content.slots)
    if log_impressions and content.slots:
        # Position is the slot's position on the page, not its index in this
        # list: a taken-down article is filtered out of the render but its
        # position was still real, and analytics that compare a lead against a
        # brief need the number to mean the same thing in every issue.
        logged = await interactions_repo.log_impressions(
            session,
            user_id=user_id,
            session_id=session_id,
            surface=AQUILA_SURFACE,
            locale=locale,
            ranking_policy=AQUILA_POLICY,
            items=[
                ImpressionToLog(
                    article_id=slot.article.id,
                    position=slot.position,
                    propensity=PROPENSITY,
                )
                for slot in content.slots
            ],
        )
        impression_ids = list(logged)

    return PageView(
        page_no=content.page_no,
        topic_id=content.topic_id,
        title=label_for(content.topic, locale) if content.topic is not None else None,
        slots=[
            SlotView(
                position=slot.position,
                role=slot.role,
                article=slot.article,
                impression_id=impression_id,
            )
            for slot, impression_id in zip(content.slots, impression_ids, strict=True)
        ],
    )
