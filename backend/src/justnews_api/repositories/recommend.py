"""Queries ranker v2 scores over (ADR 0015). Rows and counts only - how they
are weighed lives in services/scoring.py.

Candidates are fetched light: ids, source, story breadth, and the cosine to
the reader's profile computed in Postgres. Titles, snippets and embeddings
are fetched afterwards for the few rows that need them, because a pool of a
thousand full rows on every page request would spend the free database's
egress on text nobody sees.

Every reader signal is read "as of" the feed's window (`until`), so the
second page of a feed recomputes exactly the ranking the first page came
from - what happened after it does not move the rows beneath the reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import numpy as np
import numpy.typing as npt
from sqlalchemy import Select, and_, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from justnews_core.models import (
    Article,
    ArticleTopic,
    Impression,
    ImpressionView,
    InteractionEvent,
    Source,
    StoryCluster,
    UserFollow,
    UserSave,
    UserSourceFollow,
    UserStoryFollow,
)


@dataclass(frozen=True, slots=True)
class CandidateRow:
    article_id: int
    source_id: int
    story_cluster_id: int | None
    language: str
    published_at: datetime
    trust: float
    sources: int
    languages: int
    similarity: float | None


def _candidate_query(profile: list[float] | None) -> Select[Any]:
    similarity = (1 - Article.embedding.cosine_distance(profile)) if profile is not None else null()
    return (
        select(
            Article.id,
            Article.source_id,
            Article.story_cluster_id,
            Article.language,
            Article.published_at,
            Source.trust_score,
            func.coalesce(StoryCluster.source_count, 1).label("sources"),
            func.coalesce(StoryCluster.language_count, 1).label("languages"),
            similarity.label("similarity"),
        )
        .join(Source, Source.id == Article.source_id)
        .outerjoin(StoryCluster, StoryCluster.id == Article.story_cluster_id)
        .where(Article.removed_at.is_(None))
    )


def _rows(result: Any) -> list[CandidateRow]:
    return [
        CandidateRow(
            article_id=row[0],
            source_id=row[1],
            story_cluster_id=row[2],
            language=row[3],
            published_at=row[4],
            trust=float(row[5]),
            sources=int(row[6]),
            languages=int(row[7]),
            similarity=float(row[8]) if row[8] is not None else None,
        )
        for row in result.all()
    ]


async def window_candidates(
    session: AsyncSession,
    *,
    languages: list[str],
    since: datetime,
    until: datetime,
    per_source: int,
    limit: int,
    topic_ids: list[str] | None = None,
    profile: list[float] | None = None,
) -> list[CandidateRow]:
    """Everything published in (since, until], newest first, but no more than
    `per_source` from any one publisher - a pool whose mix is set by how
    often each source posts is exactly how the newest-200 pool came to hold
    64 of one publisher's briefs and none of the science desks'."""
    conditions = [
        Article.removed_at.is_(None),
        Article.published_at > since,
        Article.published_at <= until,
        Article.language.in_(languages),
    ]
    if topic_ids:
        conditions.append(
            Article.id.in_(
                select(ArticleTopic.article_id).where(ArticleTopic.topic_id.in_(topic_ids))
            )
        )
    recent = (
        select(
            Article.id.label("id"),
            func.row_number()
            .over(
                partition_by=Article.source_id,
                order_by=(Article.published_at.desc(), Article.id.desc()),
            )
            .label("rank_in_source"),
        )
        .where(*conditions)
        .subquery()
    )
    query = (
        _candidate_query(profile)
        .join(recent, recent.c.id == Article.id)
        .where(recent.c.rank_in_source <= per_source)
        .order_by(Article.published_at.desc(), Article.id.desc())
        .limit(limit)
    )
    return _rows(await session.execute(query))


async def nearest_candidates(
    session: AsyncSession,
    *,
    languages: list[str],
    since: datetime,
    until: datetime,
    profile: list[float],
    limit: int,
) -> list[CandidateRow]:
    """The articles closest to the reader's profile in the window - what a
    time-ordered pool misses when the reader's interest is a slow desk."""
    query = (
        _candidate_query(profile)
        .where(
            Article.published_at > since,
            Article.published_at <= until,
            Article.language.in_(languages),
            Article.embedding.is_not(None),
        )
        .order_by(Article.embedding.cosine_distance(profile), Article.id)
        .limit(limit)
    )
    return _rows(await session.execute(query))


async def story_candidates(
    session: AsyncSession,
    *,
    languages: list[str],
    since: datetime,
    until: datetime,
    story_ids: set[int],
    profile: list[float] | None,
) -> list[CandidateRow]:
    """Reports on stories the reader follows, so a new one reaches them."""
    if not story_ids:
        return []
    query = (
        _candidate_query(profile)
        .where(
            Article.published_at > since,
            Article.published_at <= until,
            Article.language.in_(languages),
            Article.story_cluster_id.in_(story_ids),
        )
        .order_by(Article.published_at.desc(), Article.id.desc())
        .limit(60)
    )
    return _rows(await session.execute(query))


def _as_array(value: Any) -> npt.NDArray[np.float32] | None:
    """A stored vector as float32, whichever pgvector type holds it."""
    if value is None:
        return None
    raw = value.to_numpy() if hasattr(value, "to_numpy") else value
    return np.asarray(raw, dtype=np.float32)


async def articles_with_embeddings(
    session: AsyncSession, article_ids: list[int]
) -> dict[int, tuple[int, npt.NDArray[np.float32] | None]]:
    """Each article's source and its stored vector."""
    if not article_ids:
        return {}
    result = await session.execute(
        select(Article.id, Article.source_id, Article.embedding).where(Article.id.in_(article_ids))
    )
    return {row[0]: (row[1], _as_array(row[2])) for row in result.all()}


@dataclass(frozen=True, slots=True)
class Positive:
    article_id: int
    kind: str  # "click" | "share" | "save"
    at: datetime


async def recent_positives(
    session: AsyncSession, user_id: UUID, *, until: datetime, limit: int
) -> list[Positive]:
    """The reader's most recent opens, shares and saves before `until`.
    Saves come from the saves table - saving is declarative state, not an
    event, and it is the strongest signal a reader gives."""
    events = await session.execute(
        select(
            InteractionEvent.article_id, InteractionEvent.event_type, InteractionEvent.created_at
        )
        .where(
            InteractionEvent.user_id == user_id,
            InteractionEvent.event_type.in_(("click", "share")),
            InteractionEvent.created_at < until,
        )
        .order_by(InteractionEvent.created_at.desc())
        .limit(limit)
    )
    saves = await session.execute(
        select(UserSave.article_id, UserSave.created_at)
        .where(UserSave.user_id == user_id, UserSave.created_at < until)
        .order_by(UserSave.created_at.desc())
        .limit(limit)
    )
    positives = [Positive(article_id=r[0], kind=r[1], at=r[2]) for r in events.all()]
    positives += [Positive(article_id=r[0], kind="save", at=r[1]) for r in saves.all()]
    positives.sort(key=lambda p: p.at, reverse=True)
    return positives[:limit]


async def not_interested_ids(
    session: AsyncSession, user_id: UUID, *, until: datetime | None = None
) -> set[int]:
    """Articles marked not interesting and not undone - as of `until` when
    given, so a feed's later pages rank from the same exclusions."""
    later_undo = aliased(InteractionEvent)
    undo = (
        select(later_undo.id)
        .where(
            later_undo.user_id == InteractionEvent.user_id,
            later_undo.article_id == InteractionEvent.article_id,
            later_undo.event_type == "not_interested_undo",
            later_undo.created_at > InteractionEvent.created_at,
        )
        .correlate(InteractionEvent)
    )
    query = select(InteractionEvent.article_id).where(
        InteractionEvent.user_id == user_id,
        InteractionEvent.event_type == "not_interested",
    )
    if until is not None:
        query = query.where(InteractionEvent.created_at < until)
        undo = undo.where(later_undo.created_at < until)
    query = query.where(~undo.exists())
    return set((await session.execute(query)).scalars().all())


@dataclass(frozen=True, slots=True)
class Follows:
    topics: frozenset[str]
    sources: frozenset[int]
    stories: frozenset[int]


async def follows(session: AsyncSession, user_id: UUID) -> Follows:
    topics = await session.execute(select(UserFollow.topic_id).where(UserFollow.user_id == user_id))
    sources = await session.execute(
        select(UserSourceFollow.source_id).where(UserSourceFollow.user_id == user_id)
    )
    stories = await session.execute(
        select(UserStoryFollow.story_cluster_id).where(UserStoryFollow.user_id == user_id)
    )
    return Follows(
        topics=frozenset(topics.scalars().all()),
        sources=frozenset(sources.scalars().all()),
        stories=frozenset(stories.scalars().all()),
    )


async def unopened_shows(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str | None,
    since: datetime,
    until: datetime,
) -> dict[int, int]:
    """How often each article was shown to this reader in (since, until) and
    not opened: the fatigue count. "Shown" is an impression that was seen -
    a view row - or sat in the first six positions, where a reader sees it
    whether or not the view beacon reached us. Signed-out readers are
    matched by browsing session."""
    if user_id is None and session_id is None:
        return {}
    clicked = (
        select(InteractionEvent.id)
        .where(
            InteractionEvent.impression_id == Impression.id,
            InteractionEvent.event_type == "click",
        )
        .correlate(Impression)
        .exists()
    )
    who = (
        Impression.user_id == user_id
        if user_id is not None
        else and_(Impression.user_id.is_(None), Impression.session_id == session_id)
    )
    query = (
        select(Impression.article_id, func.count())
        .outerjoin(ImpressionView, ImpressionView.impression_id == Impression.id)
        .where(
            who,
            Impression.served_at > since,
            Impression.served_at < until,
            or_(ImpressionView.impression_id.is_not(None), Impression.position < 6),
            ~clicked,
        )
        .group_by(Impression.article_id)
    )
    return {row[0]: int(row[1]) for row in (await session.execute(query)).all()}


async def opened_ids(
    session: AsyncSession, user_id: UUID, *, since: datetime, until: datetime
) -> set[int]:
    result = await session.execute(
        select(InteractionEvent.article_id).where(
            InteractionEvent.user_id == user_id,
            InteractionEvent.event_type == "click",
            InteractionEvent.created_at > since,
            InteractionEvent.created_at < until,
        )
    )
    return set(result.scalars().all())


async def views_and_clicks(
    session: AsyncSession, article_ids: list[int], *, since: datetime, until: datetime
) -> dict[int, tuple[int, int]]:
    """Per article, across readers: how many times it was seen, and opened."""
    if not article_ids:
        return {}
    views = await session.execute(
        select(Impression.article_id, func.count())
        .join(ImpressionView, ImpressionView.impression_id == Impression.id)
        .where(
            Impression.article_id.in_(article_ids),
            ImpressionView.viewed_at > since,
            ImpressionView.viewed_at < until,
        )
        .group_by(Impression.article_id)
    )
    clicks = await session.execute(
        select(InteractionEvent.article_id, func.count(func.distinct(InteractionEvent.session_id)))
        .where(
            InteractionEvent.article_id.in_(article_ids),
            InteractionEvent.event_type == "click",
            InteractionEvent.created_at > since,
            InteractionEvent.created_at < until,
        )
        .group_by(InteractionEvent.article_id)
    )
    seen = {row[0]: int(row[1]) for row in views.all()}
    opened = {row[0]: int(row[1]) for row in clicks.all()}
    return {i: (seen.get(i, 0), opened.get(i, 0)) for i in set(seen) | set(opened)}
