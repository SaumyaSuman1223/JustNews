"""Read-side queries over the content tables.

Repositories issue SQL and return rows. They hold no business rules - ranking,
filtering policy and cursor semantics live in the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, delete, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.language import tsvector_config
from justnews_core.models import (
    Article,
    ArticleTopic,
    Edition,
    InteractionEvent,
    Source,
    StoryCluster,
    Topic,
)


@dataclass(frozen=True, slots=True)
class ArticleRow:
    id: int
    title: str
    snippet: str | None
    image_url: str | None
    url_canonical: str
    language: str
    published_at: datetime
    source_id: int
    source_name: str
    source_slug: str
    story_cluster_id: int | None
    # Internal only - never exposed on ArticleOut. The Stage 5 ranker's one
    # use for it; a public API response has no business telling a client how
    # much we trust the source.
    source_trust_score: float = 0.5

    @classmethod
    def from_pair(cls, article: Article, source: Source) -> ArticleRow:
        return cls(
            id=article.id,
            title=article.title,
            snippet=article.snippet,
            image_url=article.image_url,
            url_canonical=article.url_canonical,
            language=article.language,
            published_at=article.published_at,
            source_id=source.id,
            source_name=source.name,
            source_slug=source.slug,
            story_cluster_id=article.story_cluster_id,
            source_trust_score=source.trust_score,
        )


def _base_query() -> Select[tuple[Article, Source]]:
    # The one choke point every read path shares: a taken-down article stops
    # existing for readers here, without the row itself being deleted (the
    # admin console and the audit log both need it to still be there).
    return (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.removed_at.is_(None))
    )


async def list_articles(
    session: AsyncSession,
    *,
    languages: list[str] | None,
    limit: int,
    before_published_at: datetime | None,
    before_id: int | None,
    exclude_article_ids: set[int] | None = None,
    topic_id: str | None = None,
    country: str | None = None,
) -> list[ArticleRow]:
    """Keyset pagination over ``(published_at DESC, id DESC)``.

    Keyset, not offset: on a feed that gains rows every fifteen minutes, an
    offset silently repeats and skips items as the underlying set shifts.
    """
    query = _base_query().order_by(Article.published_at.desc(), Article.id.desc()).limit(limit)

    if languages:
        query = query.where(Article.language.in_(languages))
    if exclude_article_ids:
        query = query.where(Article.id.notin_(exclude_article_ids))
    if topic_id:
        query = query.where(
            Article.id.in_(select(ArticleTopic.article_id).where(ArticleTopic.topic_id == topic_id))
        )
    if country:
        # An edition is a language *and* a place; the place lives on the
        # publisher, not the article.
        query = query.where(Source.country == country)
    if before_published_at is not None and before_id is not None:
        # sa.tuple_(), not a Python tuple. Writing
        # ``(Article.published_at, Article.id) < (ts, id)`` looks identical but
        # is evaluated by Python, not SQL: the tuple protocol compares element
        # zero first, discards the id entirely, and emits a bare
        # ``published_at < ts``. Feeds publish in batches, so articles routinely
        # share a timestamp - and every one of them after the first would be
        # silently skipped. This emits a real SQL row-value comparison, which
        # Postgres can also satisfy straight from the composite index.
        query = query.where(
            tuple_(Article.published_at, Article.id) < (before_published_at, before_id)
        )

    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


async def list_articles_window(
    session: AsyncSession,
    *,
    languages: list[str] | None,
    upper_bound: datetime,
    exclude_article_ids: set[int] | None,
    limit: int,
) -> list[ArticleRow]:
    """A bounded, reproducible candidate pool for the Stage 5 ranker:
    everything published at or before ``upper_bound``, most recent first.

    Deliberately not keyset-continued the way ``list_articles`` is. The
    ranker scores this whole window and reorders it, so "the next page" has
    no fixed relationship to any one row's ``(published_at, id)`` - what has
    to stay fixed across pages of *one ranked feed* is the window itself.
    Freezing it by bounding on ``upper_bound`` is what makes offset slicing
    into the ranked result safe: nothing published after the bound can enter
    this query, ever, so the classic offset-pagination bug (a live-growing
    table shifting rows underneath a fixed offset) cannot occur here - see
    ``services.ranking``.
    """
    query = (
        _base_query()
        .where(Article.published_at <= upper_bound)
        .order_by(Article.published_at.desc(), Article.id.desc())
        .limit(limit)
    )
    if languages:
        query = query.where(Article.language.in_(languages))
    if exclude_article_ids:
        query = query.where(Article.id.notin_(exclude_article_ids))

    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


async def get_article(session: AsyncSession, article_id: int) -> ArticleRow | None:
    result = await session.execute(_base_query().where(Article.id == article_id))
    row = result.first()
    if row is None:
        return None
    article, source = row
    return ArticleRow.from_pair(article, source)


async def get_article_including_removed(
    session: AsyncSession, article_id: int
) -> ArticleRow | None:
    """For the admin console only - every other caller must go through
    ``get_article``, which is what makes a takedown actually take an article
    down everywhere else."""
    query = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.id == article_id)
    )
    row = (await session.execute(query)).first()
    if row is None:
        return None
    article, source = row
    return ArticleRow.from_pair(article, source)


async def get_articles_by_id(
    session: AsyncSession, article_ids: list[int]
) -> dict[int, ArticleRow]:
    """Batch lookup, e.g. resolving a page of save/follow rows to articles in
    one query instead of N."""
    if not article_ids:
        return {}
    result = await session.execute(_base_query().where(Article.id.in_(set(article_ids))))
    return {article.id: ArticleRow.from_pair(article, source) for article, source in result.all()}


async def get_article_topics(session: AsyncSession, article_id: int) -> list[tuple[Topic, bool]]:
    result = await session.execute(
        select(Topic, ArticleTopic.is_primary)
        .join(ArticleTopic, ArticleTopic.topic_id == Topic.id)
        .where(ArticleTopic.article_id == article_id)
        .order_by(ArticleTopic.is_primary.desc(), Topic.id)
    )
    return list(result.tuples().all())


async def set_article_topics(
    session: AsyncSession, article_id: int, assignments: list[tuple[str, bool]]
) -> None:
    """Full replace, not a diff - the same posture the onboarding topic
    picker's own submit already takes toward a checked-box set, and the one
    that lets the editor enforce "never leave an article with zero topics"
    as a single invariant on the replacement set rather than reasoning
    about adds and removes separately.

    Stable against ingestion's own backfill: `classify.py`'s backfill only
    ever touches articles with zero `article_topics` rows (an
    `on_conflict_do_nothing` insert), so a manual override here is never
    silently reclassified - the one case that *would* look untagged to the
    backfill (deleting every topic) is exactly what the caller's
    zero-topic rejection exists to prevent.
    """
    await session.execute(delete(ArticleTopic).where(ArticleTopic.article_id == article_id))
    session.add_all(
        [
            ArticleTopic(
                article_id=article_id,
                topic_id=topic_id,
                is_primary=is_primary,
                confidence=1.0,
                assigned_by="manual",
            )
            for topic_id, is_primary in assignments
        ]
    )
    await session.flush()


async def search_articles(
    session: AsyncSession,
    *,
    query_text: str,
    languages: list[str] | None,
    limit: int,
    before_published_at: datetime | None,
    before_id: int | None,
) -> list[ArticleRow]:
    """Full text search over ``search_vector``, ranked by recency rather than
    rank - simple enough to share the exact keyset pagination ``list_articles``
    already uses, and search results skew toward "what just happened" anyway.

    The query is built with a single language's text-search configuration:
    the reader's, when exactly one was requested, so stemming matches how the
    matching articles were indexed; ``simple`` (no stemming, literal tokens)
    otherwise, which still matches exact words correctly across languages.
    """
    config = tsvector_config(languages[0]) if languages and len(languages) == 1 else "simple"
    tsquery = func.websearch_to_tsquery(config, query_text)

    query = (
        _base_query()
        .where(Article.search_vector.op("@@")(tsquery))
        .order_by(Article.published_at.desc(), Article.id.desc())
        .limit(limit)
    )
    if languages:
        query = query.where(Article.language.in_(languages))
    if before_published_at is not None and before_id is not None:
        query = query.where(
            tuple_(Article.published_at, Article.id) < (before_published_at, before_id)
        )

    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


async def list_story_clusters(
    session: AsyncSession, *, limit: int, min_sources: int
) -> list[StoryCluster]:
    """Clusters covered by several sources - the ones worth showing as a story."""
    query = (
        select(StoryCluster)
        .where(StoryCluster.source_count >= min_sources)
        .order_by(StoryCluster.last_seen_at.desc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())


async def get_story_cluster(session: AsyncSession, story_id: int) -> StoryCluster | None:
    return await session.get(StoryCluster, story_id)


async def list_articles_in_cluster(session: AsyncSession, story_id: int) -> list[ArticleRow]:
    """Every article this story clustered together - cross-lingual by
    construction, since the dedup layer that built the cluster compared
    multilingual embeddings, not text."""
    query = (
        _base_query()
        .where(Article.story_cluster_id == story_id)
        .order_by(Article.published_at.asc())
    )
    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


async def corpus_stats(session: AsyncSession) -> dict[str, int]:
    articles = await session.scalar(select(func.count()).select_from(Article))
    sources = await session.scalar(select(func.count()).select_from(Source))
    clusters = await session.scalar(select(func.count()).select_from(StoryCluster))
    languages = await session.scalar(select(func.count(func.distinct(Article.language))))
    return {
        "articles": articles or 0,
        "sources": sources or 0,
        "story_clusters": clusters or 0,
        "languages": languages or 0,
    }


@dataclass(frozen=True, slots=True)
class LanguageCoverage:
    """How much of one story is written in one language."""

    language: str
    article_count: int
    source_count: int


async def language_coverage(
    session: AsyncSession, story_ids: list[int]
) -> dict[int, list[LanguageCoverage]]:
    """Per story, how many articles and distinct sources cover it in each
    language.

    The one query behind both the coverage breakdown on a story page and the
    blindspot rail, which ask the same question from opposite directions:
    "who is covering this, and in what language" versus "which stories is
    nobody covering in the language I read".

    Ordered by article count so the dominant language of a story leads.
    """
    if not story_ids:
        return {}

    result = await session.execute(
        select(
            Article.story_cluster_id,
            Article.language,
            func.count(Article.id),
            func.count(func.distinct(Article.source_id)),
        )
        .where(Article.story_cluster_id.in_(story_ids), Article.removed_at.is_(None))
        .group_by(Article.story_cluster_id, Article.language)
        .order_by(func.count(Article.id).desc(), Article.language)
    )

    coverage: dict[int, list[LanguageCoverage]] = {story_id: [] for story_id in story_ids}
    for story_id, language, articles, sources in result.all():
        if story_id is not None:
            coverage[story_id].append(
                LanguageCoverage(language=language, article_count=articles, source_count=sources)
            )
    return coverage


async def list_blindspot_clusters(
    session: AsyncSession,
    *,
    languages: list[str],
    since: datetime,
    min_sources: int,
    limit: int,
) -> list[StoryCluster]:
    """Stories being covered, but not in any language this reader reads.

    The honest analogue of a partisan "blindspot": it counts articles that
    exist rather than scoring anyone's politics, and it is only possible
    because clustering here is cross-lingual - the same event reported in
    Spanish and Hindi collapses into one cluster, so "covered, but not for
    you" is a question the data can actually answer.

    `min_sources` guards against surfacing a single outlet's story as though
    the world were covering it; requiring zero articles in the reader's own
    languages is what makes it a blindspot rather than merely foreign news
    they have already seen.
    """
    if not languages:
        return []

    covered_here = (
        select(Article.story_cluster_id)
        .where(
            Article.story_cluster_id.is_not(None),
            Article.language.in_(languages),
            Article.removed_at.is_(None),
        )
        .scalar_subquery()
    )

    query = (
        select(StoryCluster)
        .where(
            StoryCluster.last_seen_at >= since,
            StoryCluster.source_count >= min_sources,
            StoryCluster.id.not_in(covered_here),
        )
        .order_by(StoryCluster.source_count.desc(), StoryCluster.last_seen_at.desc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())


async def list_trending(
    session: AsyncSession, *, languages: list[str] | None, since: datetime, limit: int
) -> list[ArticleRow]:
    """The most-clicked articles in a window, most-clicked first.

    Ranked on real reader behaviour rather than recency, which is what makes
    it worth showing beside a feed that is already recency-ordered - a rail
    that repeated the feed's own ordering would be decoration.

    An inner join on clicks is deliberate: an article nobody has clicked is
    not trending, and left-joining would rank the whole corpus by zero.
    """
    clicks = (
        select(
            InteractionEvent.article_id.label("article_id"),
            func.count().label("clicks"),
        )
        .where(InteractionEvent.event_type == "click", InteractionEvent.created_at >= since)
        .group_by(InteractionEvent.article_id)
        .subquery()
    )

    query = (
        _base_query()
        .join(clicks, clicks.c.article_id == Article.id)
        .order_by(clicks.c.clicks.desc(), Article.published_at.desc())
        .limit(limit)
    )
    if languages:
        query = query.where(Article.language.in_(languages))

    result = await session.execute(query)
    return [ArticleRow.from_pair(article, source) for article, source in result.all()]


async def list_editions(session: AsyncSession, *, languages: list[str] | None) -> list[Edition]:
    """The regional views on offer, default first."""
    query = select(Edition).order_by(Edition.is_default.desc(), Edition.code)
    if languages:
        query = query.where(Edition.language.in_(languages))
    return list((await session.execute(query)).scalars().all())


async def list_sources_for_language(
    session: AsyncSession, *, language: str, limit: int
) -> list[Source]:
    """Discovery order, not trust-score-as-quality-signal exposed to a reader
    - trust_score decides tie-breaking among sources that publish in the
    reader's language, it is never shown, and it is not a claim about which
    source is "better"."""
    result = await session.execute(
        select(Source)
        .where(Source.active.is_(True), Source.language == language)
        .order_by(Source.trust_score.desc(), Source.name)
        .limit(limit)
    )
    return list(result.scalars().all())
