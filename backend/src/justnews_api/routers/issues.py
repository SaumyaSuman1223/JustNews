from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import optional_user
from justnews_api.core.db import get_public_session
from justnews_api.routers.content import ArticleOut
from justnews_api.services import issues as service
from justnews_api.services.auth import Principal
from justnews_core.consent import UNCONSENTED_SESSION
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import Issue

router = APIRouter(prefix="/v1", tags=["aquila"])


class IssueEditionOut(BaseModel):
    """One edition of the Tribune, for the selector.

    Not `EditionOut`: that name is taken by the *regional* edition in
    routers/content.py, and two schemas sharing it makes the generated client
    namespace both - which silently renames the existing one and breaks every
    frontend type that referenced it. The schema layer is where ADR 0012's
    "editions is already taken" shows up in practice.
    """

    id: int
    edition_slot: str
    published_at: datetime
    published_on: date
    volume: int
    number: int

    @classmethod
    def from_row(cls, issue: Issue) -> IssueEditionOut:
        return cls(
            id=issue.id,
            edition_slot=issue.edition_slot,
            published_at=issue.published_at,
            published_on=issue.published_on,
            volume=issue.volume,
            number=issue.number,
        )


class SectionOut(BaseModel):
    page_no: int
    topic_id: str | None
    #: The section's name in the requested locale. Null on the front page,
    #: which has a masthead rather than a section head.
    title: str | None


class IssueOut(BaseModel):
    """An issue's masthead and contents. No article content - a page is a
    separate request, because a reader turns to one page at a time and
    shipping twelve pages of articles to render one is the wrong trade."""

    id: int
    locale: str
    edition_slot: str
    published_at: datetime
    published_on: date
    volume: int
    number: int
    page_count: int
    sections: list[SectionOut]


class SlotOut(BaseModel):
    position: int
    role: str
    article: ArticleOut
    impression_id: int | None


class PageOut(BaseModel):
    page_no: int
    topic_id: str | None
    title: str | None
    slots: list[SlotOut]


def _issue_out(view: service.IssueView) -> IssueOut:
    return IssueOut(
        id=view.issue.id,
        locale=view.issue.locale,
        edition_slot=view.issue.edition_slot,
        published_at=view.issue.published_at,
        published_on=view.issue.published_on,
        volume=view.issue.volume,
        number=view.issue.number,
        page_count=len(view.sections),
        sections=[
            SectionOut(page_no=s.page_no, topic_id=s.topic_id, title=s.title) for s in view.sections
        ],
    )


def _locale(value: str) -> str:
    code = normalise_language_code(value)
    if code is None:
        raise ValidationError(f"Not a language code: {value!r}")
    return code


@router.get("/issues/latest", response_model=IssueOut | None)
async def get_latest_issue(
    session: AsyncSession = Depends(get_public_session),
    locale: str = Query(default="en"),
) -> IssueOut | None:
    """The current edition of The Aquila Tribune, or null.

    Null is an ordinary response, not an error: before a locale's first
    edition, after a thin-corpus skip, or with the flag off. A publication
    that has not published yet is a real state, and 404 would make the client
    treat it as a fault.
    """
    view = await service.get_latest_issue(session, locale=_locale(locale))
    return _issue_out(view) if view is not None else None


@router.get("/issues", response_model=list[IssueEditionOut])
async def list_editions(
    session: AsyncSession = Depends(get_public_session),
    locale: str = Query(default="en"),
    on: date | None = Query(default=None, description="Defaults to the latest issue's day."),
) -> list[IssueEditionOut]:
    """The day's editions - morning, midday, evening - for the selector."""
    rows = await service.list_editions(session, locale=_locale(locale), on=on)
    return [IssueEditionOut.from_row(row) for row in rows]


@router.get("/issues/{issue_id}", response_model=IssueOut)
async def get_issue(
    issue_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_public_session),
    locale: str = Query(default="en"),
) -> IssueOut:
    """One issue by id, including a back issue still inside the retention
    window - the archive ADR 0012 buys by freezing composition."""
    return _issue_out(await service.get_issue(session, issue_id=issue_id, locale=_locale(locale)))


@router.get("/issues/{issue_id}/pages/{page_no}", response_model=PageOut)
async def get_issue_page(
    issue_id: int = Path(ge=1),
    page_no: int = Path(ge=1),
    principal: Principal | None = Depends(optional_user),
    session: AsyncSession = Depends(get_public_session),
    locale: str = Query(default="en"),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
    x_analytics_consent: str | None = Header(default=None, alias="x-analytics-consent"),
) -> PageOut:
    """One page of an issue, with its articles.

    Not behind the beta gate or `require_user`: Aquila is the same paper for
    everyone, and a signed-out reader is exactly who it is for. Impressions
    are logged against the browsing session, and only with consent - an
    unconsented reader generates no rows at all rather than rows keyed on a
    throwaway id, the same rule /v1/explore follows.
    """
    view = await service.get_page(
        session,
        issue_id=issue_id,
        page_no=page_no,
        locale=_locale(locale),
        user_id=principal.user_id if principal else None,
        session_id=x_session_id or UNCONSENTED_SESSION,
        log_impressions=x_analytics_consent == "granted",
    )
    return PageOut(
        page_no=view.page_no,
        topic_id=view.topic_id,
        title=view.title,
        slots=[
            SlotOut(
                position=slot.position,
                role=slot.role,
                article=ArticleOut.from_row(slot.article),
                impression_id=slot.impression_id,
            )
            for slot in view.slots
        ],
    )
