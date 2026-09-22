"""Three-layer deduplication and story clustering.

Layer 1 - canonical URL. Exact identity. Cheap, and catches the common case of
the same link arriving with different campaign parameters.

Layer 2 - SimHash over title shingles. Catches syndicated wire copy where the
headline is identical or near-identical but the URL differs per publisher.

Layer 3 - embedding cosine within a time window. Catches rewrites: the same
event covered independently by different newsrooms. Because the embedding is
multilingual, this layer is **cross-lingual** - the same story in English,
Spanish and Arabic collapses into one cluster (ADR 0005).

The window matters. Without it, an anniversary piece merges with the original
event a year earlier; every comparison is bounded to the last 72 hours.

Cost matters as much as correctness here. This runs once per candidate entry,
and a steady-state pass sees several hundred of them, so each layer has to stay
cheap:

* layer 1 is a unique-index lookup;
* layer 2 reads ``(id, simhash, cluster, published_at)`` for the window **once
  per run** and keeps it in memory - four scalars a row, and Hamming distance
  needs the bits rather than the article;
* layer 3 is a single pgvector nearest-neighbour query against the HNSW index.

The first implementation instead loaded every article in the window - full rows,
384-dimension vector included - for every entry, and compared them in Python.
That is O(entries x window) row loads per run and it never touched the index
built for exactly this query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, Source, StoryCluster
from justnews_core.settings import Settings
from justnews_core.text import hamming_distance

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DedupVerdict:
    """What to do with a candidate article."""

    kind: str  # "new" | "duplicate" | "cluster_member"
    existing_article_id: int | None = None
    story_cluster_id: int | None = None
    reason: str | None = None
    similarity: float | None = None

    @property
    def should_store(self) -> bool:
        return self.kind != "duplicate"


async def find_by_canonical_url(session: AsyncSession, url_canonical: str) -> Article | None:
    """Layer 1."""
    result = await session.execute(
        select(Article).where(Article.url_canonical == url_canonical).limit(1)
    )
    return result.scalar_one_or_none()


async def filter_known_urls(session: AsyncSession, urls: list[str]) -> set[str]:
    """Which of these canonical URLs we already hold.

    One indexed query for a whole feed batch, run before anything expensive
    touches an entry. In a steady state this is what removes the great majority
    of what a feed returns.
    """
    if not urls:
        return set()
    result = await session.execute(
        select(Article.url_canonical).where(Article.url_canonical.in_(set(urls)))
    )
    return set(result.scalars().all())


@dataclass(slots=True)
class RecentIndex:
    """SimHashes of everything inside the dedup window, held in memory.

    Loaded once per run rather than once per candidate. Four scalars a row,
    so the whole window costs a few tens of kilobytes - and articles stored
    during the run are added as they land, so two entries about the same event
    in one pass still collapse.

    Each row keeps its publish time so the window can be applied *between the
    two articles being compared*, not just between an article and the run's
    clock: a feed that republishes a three-week-old episode must not match
    this week's episode of the same programme just because both are in the
    same pass.
    """

    rows: list[tuple[int, int, int | None, datetime]] = field(default_factory=list)

    @classmethod
    async def load(cls, session: AsyncSession, *, since: datetime) -> RecentIndex:
        result = await session.execute(
            select(Article.id, Article.simhash, Article.story_cluster_id, Article.published_at)
            .where(Article.published_at >= since)
            .order_by(Article.published_at.desc())
        )
        return cls(rows=[(int(a), int(b), c, d) for a, b, c, d in result.all()])

    def add(
        self, article_id: int, simhash: int, cluster_id: int | None, published_at: datetime
    ) -> None:
        self.rows.append((article_id, simhash, cluster_id, published_at))

    def nearest(
        self, simhash: int, max_distance: int, *, around: datetime, window: timedelta
    ) -> tuple[int, int | None, int] | None:
        """First row within ``max_distance`` published within ``window`` of
        ``around``, as (article_id, cluster_id, distance)."""
        for article_id, other, cluster_id, published_at in self.rows:
            if abs(published_at - around) > window:
                continue
            distance = hamming_distance(simhash, other)
            if distance <= max_distance:
                return article_id, cluster_id, distance
        return None

    def __len__(self) -> int:
        return len(self.rows)


async def _nearest_by_embedding(
    session: AsyncSession, *, embedding: list[float], since: datetime, until: datetime
) -> tuple[Article, float] | None:
    """Closest article in the window by cosine distance.

    One query, ordered by pgvector's ``<=>`` operator so the HNSW index can
    serve it, rather than pulling the window into Python. Bounded on both
    sides: an old article arriving late must not join a story from days after
    it was published.
    """
    distance = Article.embedding.cosine_distance(embedding).label("distance")
    result = await session.execute(
        select(Article, distance)
        .where(
            Article.published_at >= since,
            Article.published_at <= until,
            Article.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    article, cosine_distance = row
    # pgvector returns a distance in [0, 2]; similarity is 1 - distance.
    return article, 1.0 - float(cosine_distance)


async def classify_candidate(
    session: AsyncSession,
    *,
    url_canonical: str,
    simhash: int,
    embedding: list[float] | None,
    published_at: datetime,
    settings: Settings,
    now: datetime | None = None,
    recent: RecentIndex | None = None,
) -> DedupVerdict:
    """Run all three layers in ascending order of cost.

    ``recent`` is the per-run SimHash index. Passing None loads the window for
    this call alone, which is convenient in tests and wasteful in a loop.
    """
    now = now or datetime.now(UTC)

    existing = await find_by_canonical_url(session, url_canonical)
    if existing is not None:
        return DedupVerdict(
            "duplicate",
            existing_article_id=existing.id,
            story_cluster_id=existing.story_cluster_id,
            reason="canonical_url",
        )

    window = timedelta(hours=settings.dedup_window_hours)
    anchor = min(published_at, now)
    window_start = anchor - window
    if recent is None:
        recent = await RecentIndex.load(session, since=window_start)
    if not recent:
        return DedupVerdict("new", reason="no_candidates")

    match = recent.nearest(
        simhash, settings.dedup_simhash_max_distance, around=anchor, window=window
    )
    if match is not None:
        article_id, cluster_id, distance = match
        return DedupVerdict(
            "cluster_member",
            existing_article_id=article_id,
            story_cluster_id=cluster_id,
            reason=f"simhash_distance_{distance}",
        )

    if embedding is None:
        return DedupVerdict("new", reason="no_embedding")

    nearest = await _nearest_by_embedding(
        session, embedding=embedding, since=window_start, until=anchor + window
    )
    if nearest is not None and nearest[1] >= settings.dedup_embedding_min_cosine:
        candidate, similarity = nearest
        return DedupVerdict(
            "cluster_member",
            existing_article_id=candidate.id,
            story_cluster_id=candidate.story_cluster_id,
            reason="embedding_cosine",
            similarity=round(similarity, 4),
        )

    return DedupVerdict("new", reason="below_thresholds")


async def attach_to_cluster(
    session: AsyncSession,
    *,
    article: Article,
    verdict: DedupVerdict,
    now: datetime | None = None,
) -> StoryCluster | None:
    """Put an article into a story cluster, creating one if needed.

    A cluster is only created when a *second* article joins the first: a single
    article is not a story yet, and creating one per article would make the
    table useless.
    """
    now = now or datetime.now(UTC)

    if verdict.kind != "cluster_member" or verdict.existing_article_id is None:
        return None

    sibling = await session.get(Article, verdict.existing_article_id)
    if sibling is None:
        return None

    cluster: StoryCluster | None = None
    if sibling.story_cluster_id is not None:
        cluster = await session.get(StoryCluster, sibling.story_cluster_id)

    if cluster is None:
        # country_count is left at its column default (0) here rather than
        # guessed at 1: the sibling's own country is not known without the
        # join `refresh_cluster_counts` makes a few lines down, which runs
        # unconditionally right after this and corrects it immediately.
        cluster = StoryCluster(
            title=sibling.title,
            centroid=sibling.embedding,
            first_seen_at=sibling.published_at,
            last_seen_at=sibling.published_at,
            article_count=1,
            source_count=1,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()
        sibling.story_cluster_id = cluster.id

    article.story_cluster_id = cluster.id
    await session.flush()
    await refresh_cluster_counts(session, cluster, now=now)
    return cluster


@dataclass(frozen=True, slots=True)
class _ClusterCounts:
    article_count: int
    source_count: int
    language_count: int
    country_count: int
    first_seen_at: datetime
    last_seen_at: datetime


async def _compute_cluster_counts(session: AsyncSession, cluster_id: int) -> _ClusterCounts | None:
    """The pure half of `refresh_cluster_counts`: reads, computes, assigns
    nothing. Split out so a dry run can see what *would* change without ever
    mutating the ORM object - a repair command that touched the object even
    in `--dry-run` would hand its changes to whatever `session.commit()` the
    caller's `session_scope` runs at the end, dry run or not.

    Joined to `sources` for country, which is the one count here that is not a
    property of the article itself - it belongs to the publisher. A source with
    no recorded country contributes nothing to `country_count` rather than
    counting as an "unknown" country, the same way an article's language never
    goes uncounted (language is required on every row) but a source's country
    can be genuinely absent.
    """
    result = await session.execute(
        select(Article.source_id, Article.language, Article.published_at, Source.country)
        .join(Source, Source.id == Article.source_id)
        .where(Article.story_cluster_id == cluster_id)
    )
    rows = result.all()
    if not rows:
        return None
    return _ClusterCounts(
        article_count=len(rows),
        source_count=len({row[0] for row in rows}),
        language_count=len({row[1] for row in rows}),
        country_count=len({row[3] for row in rows if row[3] is not None}),
        first_seen_at=min(row[2] for row in rows),
        last_seen_at=max(row[2] for row in rows),
    )


async def refresh_cluster_counts(
    session: AsyncSession, cluster: StoryCluster, *, now: datetime | None = None
) -> None:
    """Recount from the articles table rather than incrementing.

    Incremented counters drift the first time a write is retried; a recount over
    the handful of rows in one cluster is cheap and always correct.
    """
    counts = await _compute_cluster_counts(session, cluster.id)
    if counts is None:
        return
    cluster.article_count = counts.article_count
    cluster.source_count = counts.source_count
    cluster.language_count = counts.language_count
    cluster.country_count = counts.country_count
    cluster.first_seen_at = counts.first_seen_at
    cluster.last_seen_at = counts.last_seen_at


#: Rows fetched per round trip. `repair-snippets` timed out in production on
#: a single unbounded `select(Article)`; this pages for the same reason
#: before it can ever have the same problem.
_REPAIR_BATCH_SIZE = 500


async def repair_cluster_counts(session: AsyncSession, *, dry_run: bool = False) -> dict[str, int]:
    """Recompute every cluster's counts, including `country_count` on
    clusters that predate this column and are sitting at its default of 0.

    Data repair, not schema, for the same reasons `repair_edition_times` and
    `repair_snippets` are commands rather than migrations: re-runnable,
    reports before it writes, and every value here is fully derivable from
    `articles`/`sources` - nothing is guessed and a second run is a no-op.
    """
    examined = 0
    corrected = 0
    last_id = 0
    while True:
        batch = (
            await session.scalars(
                select(StoryCluster)
                .where(StoryCluster.id > last_id)
                .order_by(StoryCluster.id)
                .limit(_REPAIR_BATCH_SIZE)
            )
        ).all()
        if not batch:
            break
        last_id = batch[-1].id
        examined += len(batch)

        for cluster in batch:
            before = (
                cluster.article_count,
                cluster.source_count,
                cluster.language_count,
                cluster.country_count,
            )
            counts = await _compute_cluster_counts(session, cluster.id)
            if counts is None:
                continue
            after = (
                counts.article_count,
                counts.source_count,
                counts.language_count,
                counts.country_count,
            )
            if after != before:
                corrected += 1
            if not dry_run and after != before:
                cluster.article_count = counts.article_count
                cluster.source_count = counts.source_count
                cluster.language_count = counts.language_count
                cluster.country_count = counts.country_count
                cluster.first_seen_at = counts.first_seen_at
                cluster.last_seen_at = counts.last_seen_at

        if not dry_run:
            await session.flush()

    result = {"examined": examined, "corrected": corrected, "dry_run": dry_run}
    log.info("cluster_counts_repaired", **result)
    return result


#: Distinct from a moderator's takedown reason, so the admin console's
#: removed-articles list shows these for what they are.
PROGRAMME_EPISODE_REMOVAL_REASON = "automated: broadcast or podcast episode, not a news report"


async def repair_programme_episodes(
    session: AsyncSession, *, markers: tuple[str, ...], dry_run: bool = False
) -> dict[str, int | bool]:
    """Retire programme and podcast episodes already in the corpus, and the
    "stories" they formed.

    Ingestion now skips these (see ``rss.is_programme_episode``); this cleans
    up what arrived before it did. Each episode is hidden the way a takedown
    hides an article - ``removed_at`` set, row kept - with a reason that says
    it was automatic. Any cluster left with fewer than two live articles is no
    longer a story: its remaining article is detached and the cluster deleted,
    the same rule ``attach_to_cluster`` applies when it declines to create a
    cluster for a lone article. Clusters that keep two or more are recounted.
    """
    now = datetime.now(UTC)
    matching = (
        await session.scalars(
            select(Article).where(
                Article.removed_at.is_(None),
                or_(*[Article.url_canonical.contains(marker) for marker in markers]),
            )
        )
    ).all()
    affected_clusters = {a.story_cluster_id for a in matching if a.story_cluster_id is not None}

    if not dry_run:
        for article in matching:
            article.removed_at = now
            article.removed_reason = PROGRAMME_EPISODE_REMOVAL_REASON
            article.story_cluster_id = None
        await session.flush()

    dissolved = 0
    for cluster_id in affected_clusters:
        live = (
            await session.scalars(
                select(Article).where(
                    Article.story_cluster_id == cluster_id, Article.removed_at.is_(None)
                )
            )
        ).all()
        # In a dry run the episodes are still attached, so count what would remain.
        remaining = [a for a in live if a not in matching] if dry_run else list(live)
        if len(remaining) >= 2:
            if not dry_run:
                cluster = await session.get(StoryCluster, cluster_id)
                if cluster is not None:
                    await refresh_cluster_counts(session, cluster, now=now)
            continue
        dissolved += 1
        if not dry_run:
            for article in remaining:
                article.story_cluster_id = None
            await session.flush()
            cluster = await session.get(StoryCluster, cluster_id)
            if cluster is not None:
                await session.delete(cluster)

    if not dry_run:
        await session.flush()
    result: dict[str, int | bool] = {
        "episodes_removed": len(matching),
        "clusters_dissolved": dissolved,
        "dry_run": dry_run,
    }
    log.info("programme_episodes_repaired", **result)
    return result
