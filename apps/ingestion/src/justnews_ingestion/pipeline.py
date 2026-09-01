"""The ingestion run.

One pass: pick the feeds that are due, fetch them concurrently, then process
entries **serially** against the database.

The concurrency split is the important design choice. Fetching is IO-bound and
runs wide. Storage does not, because dedup compares each new article against
the ones already accepted in this same run - process two entries about the same
event in parallel and both pass the check, and the duplicate they were supposed
to prevent is written twice.

Failure isolation is the other. Every feed and every entry is wrapped: one bad
feed, one malformed entry, or one publisher that has started returning HTML
where XML used to be cannot fail the run.

The third is ordering. Entries are screened against known canonical URLs
*before* anything expensive happens to them. In a steady state almost every
entry a feed returns has already been ingested - 776 of 787 in one measured
run - so enriching first meant an HTTP fetch per article we were about to
discard.

The fourth is the deadline. This runs as a Cloud Run Job on a fifteen-minute
cron, so a pass that overruns is not merely slow - it is killed mid-write by
the job timeout or lapped by the next run. The run therefore stops itself
cleanly and records what it managed, rather than being terminated with a
half-written picture of why.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import session_scope
from justnews_core.embedding import Embedder, embed_article_text
from justnews_core.language import tsvector_config
from justnews_core.logging import get_logger
from justnews_core.models import Article, ArticleTopic, Author, Feed, IngestRun
from justnews_core.settings import Settings
from justnews_core.text import make_snippet, simhash64, slugify
from justnews_ingestion import dedup
from justnews_ingestion.classify import assign_topics
from justnews_ingestion.enrich import enrich
from justnews_ingestion.http import PoliteClient
from justnews_ingestion.rss import FeedResult, ParsedEntry, fetch_feed, is_due

log = get_logger(__name__)


@dataclass(slots=True)
class Deadline:
    """Wall-clock budget for one run."""

    expires_at: float

    @classmethod
    def after(cls, seconds: float) -> Deadline:
        return cls(expires_at=time.monotonic() + seconds)

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.expires_at - time.monotonic())


@dataclass(slots=True)
class RunStats:
    feeds_total: int = 0
    feeds_ok: int = 0
    feeds_not_modified: int = 0
    feeds_failed: int = 0
    entries_seen: int = 0
    articles_new: int = 0
    articles_duplicate: int = 0
    articles_clustered: int = 0
    articles_enriched: int = 0
    gnews_calls: int = 0
    deadline_reached: bool = False
    errors: list[str] = field(default_factory=list)


async def _due_feeds(session: AsyncSession, *, now: datetime, limit: int | None) -> list[Feed]:
    result = await session.execute(
        select(Feed).where(Feed.active.is_(True)).order_by(Feed.last_fetched_at.asc().nulls_first())
    )
    feeds = [feed for feed in result.scalars().all() if is_due(feed, now=now)]
    return feeds[:limit] if limit else feeds


async def _record_feed_outcome(session: AsyncSession, result: FeedResult, *, now: datetime) -> None:
    values: dict[str, object] = {"last_fetched_at": now}
    if result.status in ("ok", "not_modified"):
        values |= {"last_success_at": now, "consecutive_failures": 0, "last_error": None}
        if result.etag:
            values["etag"] = result.etag
        if result.last_modified:
            values["last_modified"] = result.last_modified
    else:
        values |= {
            "consecutive_failures": Feed.consecutive_failures + 1,
            "last_error": (result.error or "unknown")[:2000],
        }
    await session.execute(update(Feed).where(Feed.id == result.feed_id).values(**values))


async def _get_or_create_author(
    session: AsyncSession, source_id: int, name: str | None
) -> int | None:
    if not name:
        return None
    slug = slugify(name)
    inserted = await session.scalar(
        insert(Author)
        .values(source_id=source_id, name=name[:200], slug=slug)
        .on_conflict_do_nothing(index_elements=[Author.source_id, Author.slug])
        .returning(Author.id)
    )
    if inserted is not None:
        return int(inserted)

    # ON CONFLICT DO NOTHING returns no row when the author already exists,
    # so read it back rather than treating a known author as a failure.
    existing = await session.scalar(
        select(Author.id).where(Author.source_id == source_id, Author.slug == slug)
    )
    return int(existing) if existing is not None else None


async def store_entry(
    session: AsyncSession,
    entry: ParsedEntry,
    *,
    source_id: int,
    feed_id: int | None,
    feed_topic_hint: str | None,
    embedder: Embedder,
    settings: Settings,
    stats: RunStats,
    now: datetime,
    recent: dedup.RecentIndex | None = None,
) -> Article | None:
    """Dedup, embed, classify and store one entry. Returns None if dropped."""
    simhash = simhash64(entry.title)
    embedding = embed_article_text(embedder, entry.title, entry.snippet)

    verdict = await dedup.classify_candidate(
        session,
        url_canonical=entry.url_canonical,
        simhash=simhash,
        embedding=embedding,
        published_at=entry.published_at,
        settings=settings,
        now=now,
        recent=recent,
    )
    if not verdict.should_store:
        # Already counted by the URL screen for the common case; this catches
        # a URL that appeared twice inside one batch.
        stats.articles_duplicate += 1
        return None

    author_id = await _get_or_create_author(session, source_id, entry.author_name)

    article = Article(
        url_canonical=entry.url_canonical,
        title=entry.title[:2000],
        snippet=make_snippet(entry.snippet, settings.ingest_snippet_max_chars),
        image_url=entry.image_url,
        source_id=source_id,
        feed_id=feed_id,
        author_id=author_id,
        language=entry.language,
        published_at=entry.published_at,
        fetched_at=now,
        simhash=simhash,
        embedding=embedding,
        search_vector=func.to_tsvector(
            tsvector_config(entry.language), f"{entry.title} {entry.snippet or ''}"
        ),
    )
    session.add(article)
    await session.flush()
    stats.articles_new += 1
    if recent is not None:
        # So that two entries about one event in the same pass still collapse.
        recent.add(article.id, simhash, article.story_cluster_id)

    if verdict.kind == "cluster_member":
        cluster = await dedup.attach_to_cluster(session, article=article, verdict=verdict, now=now)
        if cluster is not None:
            stats.articles_clustered += 1
            log.debug(
                "article_clustered",
                article_id=article.id,
                cluster_id=cluster.id,
                reason=verdict.reason,
                similarity=verdict.similarity,
            )

    for assignment in await assign_topics(
        session,
        source_id=source_id,
        raw_categories=entry.raw_categories,
        feed_topic_hint=feed_topic_hint,
        title=entry.title,
        snippet=entry.snippet,
    ):
        await session.execute(
            insert(ArticleTopic)
            .values(
                article_id=article.id,
                topic_id=assignment.topic_id,
                confidence=assignment.confidence,
                is_primary=assignment.is_primary,
                assigned_by=assignment.assigned_by,
            )
            .on_conflict_do_nothing(index_elements=[ArticleTopic.article_id, ArticleTopic.topic_id])
        )

    return article


async def run_ingestion(
    settings: Settings,
    embedder: Embedder,
    *,
    feed_limit: int | None = None,
    enrich_articles: bool = True,
    trigger: str = "cron",
) -> RunStats:
    """One full ingestion pass. Records an ``ingest_runs`` row either way."""
    now = datetime.now(UTC)
    stats = RunStats()
    deadline = Deadline.after(settings.ingest_run_deadline_seconds)
    enrich_budget = settings.ingest_max_enrich_per_run if enrich_articles else 0
    window_start = now - timedelta(hours=settings.dedup_window_hours)

    async with session_scope() as session:
        run = IngestRun(started_at=now, trigger=trigger)
        session.add(run)
        await session.flush()
        run_id = run.id
        feeds = await _due_feeds(session, now=now, limit=feed_limit)
        stats.feeds_total = len(feeds)
        feed_meta = {
            feed.id: (feed.source_id, feed.topic_hint_id, feed.url, feed.language) for feed in feeds
        }
        # Loaded once for the whole run, not once per candidate entry.
        recent = await dedup.RecentIndex.load(session, since=window_start)

    log.info("dedup_window_loaded", articles=len(recent), hours=settings.dedup_window_hours)

    log.info("ingest_run_started", run_id=run_id, feeds_due=stats.feeds_total)

    if feeds:
        async with PoliteClient(settings) as client:
            results = await _fetch_all(client, feeds, settings)

            for result in results:
                if result.status == "ok":
                    stats.feeds_ok += 1
                elif result.status == "not_modified":
                    stats.feeds_not_modified += 1
                else:
                    stats.feeds_failed += 1
                    if result.error:
                        stats.errors.append(f"feed {result.feed_id}: {result.error}")

                async with session_scope() as session:
                    await _record_feed_outcome(session, result, now=datetime.now(UTC))

                if result.status != "ok" or not result.entries:
                    continue

                if deadline.expired:
                    stats.deadline_reached = True
                    log.warning(
                        "ingest_deadline_reached",
                        run_id=run_id,
                        entries_seen=stats.entries_seen,
                        articles_new=stats.articles_new,
                    )
                    break

                source_id, topic_hint, _, _ = feed_meta[result.feed_id]
                enrich_budget -= await _store_feed_entries(
                    result,
                    source_id=source_id,
                    topic_hint=topic_hint,
                    client=client,
                    embedder=embedder,
                    settings=settings,
                    stats=stats,
                    enrich_budget=enrich_budget,
                    deadline=deadline,
                    recent=recent,
                )

    async with session_scope() as session:
        await session.execute(
            update(IngestRun)
            .where(IngestRun.id == run_id)
            .values(
                finished_at=datetime.now(UTC),
                feeds_total=stats.feeds_total,
                feeds_ok=stats.feeds_ok,
                feeds_not_modified=stats.feeds_not_modified,
                feeds_failed=stats.feeds_failed,
                entries_seen=stats.entries_seen,
                articles_new=stats.articles_new,
                articles_duplicate=stats.articles_duplicate,
                articles_clustered=stats.articles_clustered,
                articles_enriched=stats.articles_enriched,
                deadline_reached=stats.deadline_reached,
                gnews_calls=stats.gnews_calls,
                error="\n".join(stats.errors[:20]) or None,
            )
        )

    log.info(
        "ingest_run_finished",
        run_id=run_id,
        feeds_ok=stats.feeds_ok,
        feeds_failed=stats.feeds_failed,
        articles_new=stats.articles_new,
        articles_duplicate=stats.articles_duplicate,
        articles_clustered=stats.articles_clustered,
    )
    return stats


async def _fetch_all(
    client: PoliteClient, feeds: list[Feed], settings: Settings
) -> list[FeedResult]:
    """Fetch every due feed, bounded concurrency, isolated failures."""
    semaphore = asyncio.Semaphore(settings.ingest_max_feed_concurrency)

    async def one(feed: Feed) -> FeedResult:
        async with semaphore:
            return await fetch_feed(client, feed, settings)

    gathered = await asyncio.gather(*(one(feed) for feed in feeds), return_exceptions=True)

    results: list[FeedResult] = []
    for feed, outcome in zip(feeds, gathered, strict=True):
        if isinstance(outcome, BaseException):
            log.exception("feed_task_crashed", feed_id=feed.id, exc_info=outcome)
            results.append(FeedResult(feed.id, "failed", error=f"task: {outcome!r}"))
        else:
            results.append(outcome)
    return results


async def _store_feed_entries(
    result: FeedResult,
    *,
    source_id: int,
    topic_hint: str | None,
    client: PoliteClient,
    embedder: Embedder,
    settings: Settings,
    stats: RunStats,
    enrich_budget: int,
    deadline: Deadline,
    recent: dedup.RecentIndex,
) -> int:
    """Store one feed's entries. Returns how much of the enrich budget it used.

    Order matters more than anything else in this function.

    First, entries whose canonical URL we already hold are dropped. That is a
    unique-index lookup, and in a steady state it removes almost everything a
    feed returns - so it must happen before we spend an HTTP request, an
    embedding or a transaction on them.

    Then the survivors that are missing an image or a summary are enriched,
    concurrently: ``PoliteClient`` already serialises per host, so doing this
    inline in the storage loop bought nothing and made a pass take longer than
    the interval between runs.

    Storage stays serial and one transaction per entry. Serial because dedup
    compares each candidate against what this run has already accepted; one
    transaction each because an entry that violates a constraint should roll
    back alone, not discard the fifty good ones fetched beside it.
    """
    async with session_scope() as session:
        known = await dedup.filter_known_urls(
            session, [entry.url_canonical for entry in result.entries]
        )

    fresh = [entry for entry in result.entries if entry.url_canonical not in known]
    stats.entries_seen += len(result.entries)
    stats.articles_duplicate += len(result.entries) - len(fresh)
    if not fresh:
        return 0

    to_enrich = [entry for entry in fresh if not entry.image_url or not entry.snippet][
        : max(0, enrich_budget)
    ]
    if to_enrich and not deadline.expired:
        await _enrich_batch(
            to_enrich, client=client, settings=settings, stats=stats, deadline=deadline
        )

    for entry in fresh:
        if deadline.expired:
            stats.deadline_reached = True
            break
        try:
            async with session_scope() as session:
                await store_entry(
                    session,
                    entry,
                    source_id=source_id,
                    feed_id=result.feed_id,
                    feed_topic_hint=topic_hint,
                    embedder=embedder,
                    settings=settings,
                    stats=stats,
                    now=datetime.now(UTC),
                    recent=recent,
                )
        except Exception as exc:
            stats.errors.append(f"entry {entry.url_canonical}: {type(exc).__name__}: {exc}")
            log.warning("entry_store_failed", url=entry.url_canonical, error=type(exc).__name__)

    return len(to_enrich)


async def _enrich_batch(
    entries: list[ParsedEntry],
    *,
    client: PoliteClient,
    settings: Settings,
    stats: RunStats,
    deadline: Deadline,
) -> None:
    """Fill in missing images, summaries and canonical URLs, best-effort.

    Never raises and never blocks the run: enrichment improves an article the
    feed already gave us, so anything that fails is simply left as it was.
    """
    semaphore = asyncio.Semaphore(settings.ingest_max_enrich_concurrency)

    async def one(entry: ParsedEntry) -> None:
        if deadline.expired:
            return
        async with semaphore:
            metadata = await enrich(client, entry.url_canonical, settings)
        if metadata.canonical_url:
            entry.url_canonical = metadata.canonical_url
        entry.image_url = entry.image_url or metadata.image_url
        entry.snippet = entry.snippet or metadata.description
        entry.author_name = entry.author_name or metadata.author_name
        if metadata.image_url or metadata.description:
            stats.articles_enriched += 1

    try:
        async with asyncio.timeout(deadline.remaining_seconds):
            await asyncio.gather(*(one(entry) for entry in entries), return_exceptions=True)
    except TimeoutError:
        stats.deadline_reached = True
        log.warning("enrichment_deadline_reached", pending=len(entries))
