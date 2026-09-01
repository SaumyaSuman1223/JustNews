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
* layer 2 reads ``(id, simhash, cluster)`` for the window **once per run** and
  keeps it in memory - three integers a row, and Hamming distance needs the bits
  rather than the article;
* layer 3 is a single pgvector nearest-neighbour query against the HNSW index.

The first implementation instead loaded every article in the window - full rows,
384-dimension vector included - for every entry, and compared them in Python.
That is O(entries x window) row loads per run and it never touched the index
built for exactly this query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, StoryCluster
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

    Loaded once per run rather than once per candidate. Three integers a row,
    so the whole window costs a few tens of kilobytes - and articles stored
    during the run are added as they land, so two entries about the same event
    in one pass still collapse.
    """

    rows: list[tuple[int, int, int | None]] = field(default_factory=list)

    @classmethod
    async def load(cls, session: AsyncSession, *, since: datetime) -> RecentIndex:
        result = await session.execute(
            select(Article.id, Article.simhash, Article.story_cluster_id)
            .where(Article.published_at >= since)
            .order_by(Article.published_at.desc())
        )
        return cls(rows=[(int(a), int(b), c) for a, b, c in result.all()])

    def add(self, article_id: int, simhash: int, cluster_id: int | None) -> None:
        self.rows.append((article_id, simhash, cluster_id))

    def nearest(self, simhash: int, max_distance: int) -> tuple[int, int | None, int] | None:
        """First row within ``max_distance``, as (article_id, cluster_id, distance)."""
        for article_id, other, cluster_id in self.rows:
            distance = hamming_distance(simhash, other)
            if distance <= max_distance:
                return article_id, cluster_id, distance
        return None

    def __len__(self) -> int:
        return len(self.rows)


async def _nearest_by_embedding(
    session: AsyncSession, *, embedding: list[float], since: datetime
) -> tuple[Article, float] | None:
    """Closest article in the window by cosine distance.

    One query, ordered by pgvector's ``<=>`` operator so the HNSW index can
    serve it, rather than pulling the window into Python.
    """
    distance = Article.embedding.cosine_distance(embedding).label("distance")
    result = await session.execute(
        select(Article, distance)
        .where(Article.published_at >= since, Article.embedding.is_not(None))
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

    window_start = min(published_at, now) - timedelta(hours=settings.dedup_window_hours)
    if recent is None:
        recent = await RecentIndex.load(session, since=window_start)
    if not recent:
        return DedupVerdict("new", reason="no_candidates")

    match = recent.nearest(simhash, settings.dedup_simhash_max_distance)
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

    nearest = await _nearest_by_embedding(session, embedding=embedding, since=window_start)
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


async def refresh_cluster_counts(
    session: AsyncSession, cluster: StoryCluster, *, now: datetime | None = None
) -> None:
    """Recount from the articles table rather than incrementing.

    Incremented counters drift the first time a write is retried; a recount over
    the handful of rows in one cluster is cheap and always correct.
    """
    result = await session.execute(
        select(Article.source_id, Article.language, Article.published_at).where(
            Article.story_cluster_id == cluster.id
        )
    )
    rows = result.all()
    if not rows:
        return

    cluster.article_count = len(rows)
    cluster.source_count = len({row[0] for row in rows})
    cluster.language_count = len({row[1] for row in rows})
    cluster.first_seen_at = min(row[2] for row in rows)
    cluster.last_seen_at = max(row[2] for row in rows)
