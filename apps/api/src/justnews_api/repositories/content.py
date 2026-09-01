"""Read-side queries over the content tables.

Repositories issue SQL and return rows. They hold no business rules - ranking,
filtering policy and cursor semantics live in the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.language import tsvector_config
from justnews_core.models import Article, ArticleTopic, Source, StoryCluster


@dataclass(frozen=True, slots=True)
class ArticleRow:
    id: int
    title: str
    snippet: str | None
    image_url: str | None
    url_canonical: str
    language: str
    published_at: datetime
    source_name: str
    source_slug: str
    story_cluster_id: int | None

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
            source_name=source.name,
            source_slug=source.slug,
            story_cluster_id=article.story_cluster_id,
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
