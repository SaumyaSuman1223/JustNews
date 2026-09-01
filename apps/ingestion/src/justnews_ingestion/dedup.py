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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.embedding import cosine_similarity
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


async def _recent_candidates(
    session: AsyncSession, *, since: datetime, limit: int = 3000
) -> list[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.published_at >= since)
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def classify_candidate(
    session: AsyncSession,
    *,
    url_canonical: str,
    simhash: int,
    embedding: list[float] | None,
    published_at: datetime,
    settings: Settings,
    now: datetime | None = None,
) -> DedupVerdict:
    """Run all three layers in ascending order of cost."""
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
    candidates = await _recent_candidates(session, since=window_start)
    if not candidates:
        return DedupVerdict("new", reason="no_candidates")

    for candidate in candidates:
        distance = hamming_distance(simhash, candidate.simhash)
        if distance <= settings.dedup_simhash_max_distance:
            return DedupVerdict(
                "cluster_member",
                existing_article_id=candidate.id,
                story_cluster_id=candidate.story_cluster_id,
                reason=f"simhash_distance_{distance}",
            )

    if embedding is None:
        return DedupVerdict("new", reason="no_embedding")

    best: tuple[float, Article] | None = None
    for candidate in candidates:
        if candidate.embedding is None:
            continue
        similarity = cosine_similarity(embedding, [float(x) for x in candidate.embedding])
        if best is None or similarity > best[0]:
            best = (similarity, candidate)

    if best is not None and best[0] >= settings.dedup_embedding_min_cosine:
        similarity, candidate = best
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
