"""Composing an issue of The Aquila Tribune.

Run three times a day from `.github/workflows/aquila.yml`, once per locale
per edition slot. The output is an immutable `issues` row with its pages and
slots (ADR 0012); nothing here is ever consulted on a reader's request.

**Why the composer lives in ingestion rather than reusing the API's ranker.**
`justnews_api.services.ranking` is a *serving* concern: it scores candidates
for one reader using followed topics, click history and a seen-penalty, then
diversifies with MMR. Aquila has no reader - every subscriber to a locale
gets the same paper - so none of those inputs exist. What it needs instead is
an editorial selection: the strongest recent story per section, one article
per story cluster, no single source dominating a page. That is a genuinely
different algorithm, and `apps/` importing from `backend/` to reach a ranker
whose signals are all empty would buy a layering violation for nothing.

**Why each edition looks different.** The window is "since the previous
edition", so the Midday Edition is what changed since morning rather than a
reshuffle of the same corpus. That is what makes three editions three
moments instead of three views of one pile. On a thin corpus the window
widens (see `_window_start`) rather than publishing an empty paper.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, ArticleTopic, Issue, IssuePage, IssueSlot, Source

log = get_logger(__name__)

# The three moments (direction doc §9). Hours are UTC: the composer runs on a
# GitHub Actions cron, which is UTC, and a locale-local publish time is a
# refinement for when there is more than one region to serve.
EDITION_SLOTS: dict[str, int] = {"morning": 6, "midday": 14, "evening": 22}

# The running order, as IPTC top-level concept IDs (ADR 0006 - the ID is the
# canonical key; the page's displayed name is this topic's label in the
# reader's locale, looked up at render time). Ordered the way a paper orders
# its sections, and truncated to whatever the corpus can actually fill: a
# section with too little to say is dropped, not padded.
SECTION_ORDER: tuple[str, ...] = (
    "medtop:11000000",  # Politics
    "medtop:16000000",  # Conflict, war and peace
    "medtop:04000000",  # Economy, business and finance
    "medtop:13000000",  # Science and technology
    "medtop:07000000",  # Health
    "medtop:06000000",  # Environment
    "medtop:14000000",  # Society
    "medtop:01000000",  # Arts, culture, entertainment and media
    "medtop:15000000",  # Sport
)

FRONT_PAGE_LEADS = 1
FRONT_PAGE_SECONDARIES = 4
FRONT_PAGE_BRIEFS = 7
SECTION_LEADS = 1
SECTION_SECONDARIES = 5
MAX_SECTION_PAGES = 8

# A section page needs at least this many articles to be worth printing.
MIN_SECTION_ARTICLES = 3
# No page may run more than this many pieces from one outlet. A section where
# one publisher supplies everything is a press release, not a page.
MAX_PER_SOURCE_PER_PAGE = 2
# How far back to look when the slot's own window is too thin to fill a paper.
FALLBACK_WINDOW_HOURS = 48
# Below this, the corpus cannot support an issue and the composer publishes
# nothing rather than a paper with two stories in it.
MIN_ARTICLES_FOR_ISSUE = 8


@dataclass(frozen=True, slots=True)
class ComposeResult:
    issue_id: int | None
    locale: str
    edition_slot: str
    published_on: date
    volume: int
    number: int
    pages: int
    articles: int
    skipped_reason: str | None = None


def _window_start(now: datetime, edition_slot: str) -> datetime:
    """The start of this edition's coverage window.

    Each edition covers what happened since the previous one, which on the
    current schedule is eight hours for all three (06:00 → 14:00 → 22:00 →
    06:00). Computed from `EDITION_SLOTS` rather than hard-coded, so moving a
    publish time moves its window with it.
    """
    hours = sorted(EDITION_SLOTS.values())
    current = EDITION_SLOTS[edition_slot]
    index = hours.index(current)
    previous = hours[index - 1]
    # index 0 wraps to the last slot, which was yesterday.
    delta = (current - previous) % 24
    return now - timedelta(hours=delta or 24)


async def _candidates(
    session: AsyncSession,
    *,
    language: str,
    since: datetime,
    topic_id: str | None,
    limit: int,
) -> list[tuple[int, int, int | None]]:
    """`(article_id, source_id, story_cluster_id)` for one section, best first.

    Ordering is recency weighted by source trust rather than recency alone:
    on a corpus built from hundreds of feeds, "newest" is dominated by
    whichever aggregator posts most often, which is not the same as
    "most worth the front page".
    """
    stmt = (
        select(Article.id, Article.source_id, Article.story_cluster_id)
        .join(Source, Source.id == Article.source_id)
        .where(
            Article.language == language,
            Article.published_at >= since,
            Article.removed_at.is_(None),
        )
        # Recency in hours, discounted by trust: a trusted source's two-hour-
        # old piece outranks an untrusted source's one-hour-old piece.
        .order_by(
            (
                func.extract("epoch", func.now() - Article.published_at)
                / (0.5 + Source.trust_score)
            ).asc()
        )
        .limit(limit)
    )
    if topic_id is not None:
        stmt = stmt.where(
            Article.id.in_(select(ArticleTopic.article_id).where(ArticleTopic.topic_id == topic_id))
        )
    rows = await session.execute(stmt)
    return [(r[0], r[1], r[2]) for r in rows.all()]


def _select_for_page(
    candidates: list[tuple[int, int, int | None]],
    *,
    wanted: int,
    used_articles: set[int],
    used_clusters: set[int],
    per_source: dict[int, int],
) -> list[int]:
    """Take up to `wanted` articles, one per story cluster, capped per source.

    The cluster rule is what stops a page running the same wire story three
    times under three mastheads; the source cap is what stops one outlet
    owning a section. Both are applied here rather than in SQL because they
    are stateful across the whole issue - a story that led the front page
    must not lead a section page as well.

    `per_source` is owned by the caller and shared across a page's roles.
    Held locally it would reset between the lead, secondary and brief runs,
    and one outlet could take the cap in each of them - three times the
    intended limit on a single page.
    """
    chosen: list[int] = []
    for article_id, source_id, cluster_id in candidates:
        if len(chosen) >= wanted:
            break
        if article_id in used_articles:
            continue
        if cluster_id is not None and cluster_id in used_clusters:
            continue
        if per_source.get(source_id, 0) >= MAX_PER_SOURCE_PER_PAGE:
            continue
        chosen.append(article_id)
        per_source[source_id] = per_source.get(source_id, 0) + 1
        used_articles.add(article_id)
        if cluster_id is not None:
            used_clusters.add(cluster_id)
    return chosen


async def _next_number(session: AsyncSession, *, locale: str, volume: int) -> int:
    """This issue's ordinal within its volume. Derived, not stored state."""
    count = await session.scalar(
        select(func.count())
        .select_from(Issue)
        .where(Issue.locale == locale, Issue.volume == volume)
    )
    return int(count or 0) + 1


async def compose_issue(
    session: AsyncSession,
    *,
    locale: str,
    edition_slot: str,
    now: datetime | None = None,
) -> ComposeResult:
    """Compose and persist one issue. Idempotent per (locale, day, slot).

    Returns a result with `skipped_reason` set rather than raising when there
    is nothing to publish - a thin corpus is an ordinary Tuesday for a
    free-tier aggregator, not an error, and the workflow should not go red
    for it. The Aquila route renders its "no issue yet" state instead.
    """
    if edition_slot not in EDITION_SLOTS:
        raise ValueError(f"Unknown edition slot: {edition_slot!r}")

    now = now or datetime.now(UTC)
    published_on = now.date()

    existing = await session.scalar(
        select(Issue.id).where(
            Issue.locale == locale,
            Issue.published_on == published_on,
            Issue.edition_slot == edition_slot,
        )
    )
    if existing is not None:
        log.info("aquila_issue_exists", issue_id=existing, locale=locale, slot=edition_slot)
        return ComposeResult(
            issue_id=existing,
            locale=locale,
            edition_slot=edition_slot,
            published_on=published_on,
            volume=0,
            number=0,
            pages=0,
            articles=0,
            skipped_reason="already_published",
        )

    since = _window_start(now, edition_slot)
    front = await _candidates(session, language=locale, since=since, topic_id=None, limit=120)
    if len(front) < MIN_ARTICLES_FOR_ISSUE:
        # Widen before giving up: an eight-hour window on a quiet night can
        # be genuinely empty without the corpus being empty.
        since = now - timedelta(hours=FALLBACK_WINDOW_HOURS)
        front = await _candidates(session, language=locale, since=since, topic_id=None, limit=120)

    if len(front) < MIN_ARTICLES_FOR_ISSUE:
        log.warning(
            "aquila_corpus_too_thin",
            locale=locale,
            slot=edition_slot,
            available=len(front),
            needed=MIN_ARTICLES_FOR_ISSUE,
        )
        return ComposeResult(
            issue_id=None,
            locale=locale,
            edition_slot=edition_slot,
            published_on=published_on,
            volume=0,
            number=0,
            pages=0,
            articles=0,
            skipped_reason="corpus_too_thin",
        )

    # Volume is the year offset, so masthead numbering needs no stored
    # counter that could drift: 2026 is Volume 1.
    volume = now.year - 2025
    number = await _next_number(session, locale=locale, volume=volume)

    issue = Issue(
        locale=locale,
        edition_slot=edition_slot,
        published_on=published_on,
        published_at=now,
        volume=volume,
        number=number,
    )
    session.add(issue)
    await session.flush()

    used_articles: set[int] = set()
    used_clusters: set[int] = set()
    total_articles = 0

    # Page 1: the front, drawn from the whole corpus.
    front_page = IssuePage(issue_id=issue.id, page_no=1, topic_id=None)
    session.add(front_page)
    await session.flush()

    position = 0
    front_per_source: dict[int, int] = {}
    for role, wanted in (
        ("lead", FRONT_PAGE_LEADS),
        ("secondary", FRONT_PAGE_SECONDARIES),
        ("brief", FRONT_PAGE_BRIEFS),
    ):
        for article_id in _select_for_page(
            front,
            wanted=wanted,
            used_articles=used_articles,
            used_clusters=used_clusters,
            per_source=front_per_source,
        ):
            session.add(
                IssueSlot(
                    page_id=front_page.id,
                    position=position,
                    article_id=article_id,
                    role=role,
                )
            )
            position += 1
            total_articles += 1

    # Section pages, in the running order, skipping any the corpus cannot fill.
    page_no = 2
    for topic_id in SECTION_ORDER:
        if page_no > MAX_SECTION_PAGES + 1:
            break
        section = await _candidates(
            session, language=locale, since=since, topic_id=topic_id, limit=60
        )
        available = [c for c in section if c[0] not in used_articles]
        if len(available) < MIN_SECTION_ARTICLES:
            continue

        page = IssuePage(issue_id=issue.id, page_no=page_no, topic_id=topic_id)
        session.add(page)
        await session.flush()

        position = 0
        page_per_source: dict[int, int] = {}
        for role, wanted in (("lead", SECTION_LEADS), ("secondary", SECTION_SECONDARIES)):
            for article_id in _select_for_page(
                section,
                wanted=wanted,
                used_articles=used_articles,
                used_clusters=used_clusters,
                per_source=page_per_source,
            ):
                session.add(
                    IssueSlot(page_id=page.id, position=position, article_id=article_id, role=role)
                )
                position += 1
                total_articles += 1
        page_no += 1

    pages = page_no - 1
    log.info(
        "aquila_issue_composed",
        issue_id=issue.id,
        locale=locale,
        slot=edition_slot,
        volume=volume,
        number=number,
        pages=pages,
        articles=total_articles,
        window_start=since.isoformat(),
    )
    return ComposeResult(
        issue_id=issue.id,
        locale=locale,
        edition_slot=edition_slot,
        published_on=published_on,
        volume=volume,
        number=number,
        pages=pages,
        articles=total_articles,
    )


def current_slot(now: datetime | None = None) -> str:
    """The edition slot whose publish time has most recently passed."""
    now = now or datetime.now(UTC)
    passed = [(hour, name) for name, hour in EDITION_SLOTS.items() if hour <= now.hour]
    if not passed:
        # Before 06:00 UTC the most recent edition is last night's evening.
        return "evening"
    return max(passed)[1]
