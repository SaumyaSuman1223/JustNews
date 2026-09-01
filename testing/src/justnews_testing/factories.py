"""Minimal object builders for tests. Not a factory library - just enough to
keep the arrange step of each test to one line."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.embedding import HashingEmbedder, embed_article_text
from justnews_core.language import tsvector_config
from justnews_core.models import Article, Source, Topic
from justnews_core.text import canonicalise_url, simhash64

_embedder = HashingEmbedder()

# A monotonic counter, not hash(title): Python's string hash is randomised per
# process, and two articles in the same test can collide on the unique URL.
_counter = itertools.count(1)


async def make_source(session: AsyncSession, slug: str = "test-source", **kwargs: object) -> Source:
    source = Source(
        slug=slug,
        name=kwargs.pop("name", slug.replace("-", " ").title()),  # type: ignore[arg-type]
        homepage_url=f"https://{slug}.example",
        language=kwargs.pop("language", "en"),  # type: ignore[arg-type]
        country=kwargs.pop("country", "GB"),  # type: ignore[arg-type]
        trust_score=kwargs.pop("trust_score", 0.8),  # type: ignore[arg-type]
        **kwargs,
    )
    session.add(source)
    await session.flush()
    return source


async def make_article(
    session: AsyncSession,
    source: Source,
    *,
    title: str = "A headline",
    url: str | None = None,
    language: str = "en",
    published_at: datetime | None = None,
    minutes_ago: int = 0,
    snippet: str | None = None,
) -> Article:
    published_at = published_at or datetime.now(UTC) - timedelta(minutes=minutes_ago)
    article = Article(
        url_canonical=canonicalise_url(url or f"https://{source.slug}.example/{next(_counter)}"),
        title=title,
        snippet=snippet,
        source_id=source.id,
        language=language,
        published_at=published_at,
        fetched_at=datetime.now(UTC),
        simhash=simhash64(title),
        embedding=embed_article_text(_embedder, title, snippet),
        search_vector=func.to_tsvector(tsvector_config(language), f"{title} {snippet or ''}"),
    )
    session.add(article)
    await session.flush()
    return article


async def make_topic(
    session: AsyncSession, topic_id: str = "medtop:99000001", slug: str = "test-topic"
) -> Topic:
    topic = Topic(id=topic_id, level=1, path=[topic_id], slug=slug)
    session.add(topic)
    await session.flush()
    return topic
