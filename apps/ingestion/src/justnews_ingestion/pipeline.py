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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

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
class RunStats:
    feeds_total: int = 0
    feeds_ok: int = 0
    feeds_not_modified: int = 0
    feeds_failed: int = 0
    entries_seen: int = 0
    articles_new: int = 0
    articles_duplicate: int = 0
    articles_clustered: int = 0
    gnews_calls: int = 0
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
    )
    if not verdict.should_store:
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

                source_id, topic_hint, _, _ = feed_meta[result.feed_id]
                await _store_feed_entries(
                    result,
                    source_id=source_id,
                    topic_hint=topic_hint,
                    client=client,
                    embedder=embedder,
                    settings=settings,
                    stats=stats,
                    enrich_articles=enrich_articles,
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
    import asyncio

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
    enrich_articles: bool,
) -> None:
    """Store one feed's entries, one transaction per entry.

    Per-entry transactions cost a little throughput and buy a lot: a single
    entry that violates a constraint rolls back alone instead of discarding the
    fifty good ones fetched alongside it.
    """
    for entry in result.entries:
        stats.entries_seen += 1
        try:
            if enrich_articles and (not entry.image_url or not entry.snippet):
                metadata = await enrich(client, entry.url_canonical, settings)
                if metadata.canonical_url:
                    entry.url_canonical = metadata.canonical_url
                entry.image_url = entry.image_url or metadata.image_url
                entry.snippet = entry.snippet or metadata.description
                entry.author_name = entry.author_name or metadata.author_name

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
                )
        except Exception as exc:
            stats.errors.append(f"entry {entry.url_canonical}: {type(exc).__name__}: {exc}")
            log.warning("entry_store_failed", url=entry.url_canonical, error=type(exc).__name__)
