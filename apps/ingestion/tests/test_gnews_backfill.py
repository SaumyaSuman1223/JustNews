"""`run_ingestion`'s GNews backfill step, against a real database.

No due feeds exist in a freshly truncated test database, so `run_ingestion`
here exercises only the backfill path - the RSS loop has nothing to do.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from justnews_testing.factories import make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import dispose_engine, init_engine
from justnews_core.embedding import HashingEmbedder
from justnews_core.models import Article, ArticleTopic, Source
from justnews_core.settings import Settings
from justnews_ingestion import gnews
from justnews_ingestion.pipeline import run_ingestion
from justnews_ingestion.rss import ParsedEntry

EMBEDDER = HashingEmbedder()


@pytest.fixture
async def app_engine(database: str):
    """Point run_ingestion's own session_scope() at the same test database the
    `session` fixture uses, so writes made through one are visible to the
    other - they're separate connections to the same real Postgres."""
    init_engine(Settings(database_url=database))  # type: ignore[arg-type]
    yield
    await dispose_engine()


@pytest.fixture
async def backfill_topics(session: AsyncSession) -> None:
    """The IPTC concepts GNews categories map onto.

    article_topics.topic_id is a foreign key, so backfill that attributes a
    topic needs these rows to exist - seeding is what supplies them in
    production.
    """
    for topic_id, slug in [
        ("medtop:04000000", "economy"),
        ("medtop:13000000", "sci-tech"),
        ("medtop:07000000", "health"),
        ("medtop:15000000", "sport"),
        ("medtop:01000000", "arts"),
    ]:
        await make_topic(session, topic_id=topic_id, slug=slug)
    await session.commit()


class TestGnewsBackfill:
    async def test_no_api_key_spends_nothing(
        self, database: str, session: AsyncSession, app_engine: None
    ) -> None:
        settings = Settings(database_url=database, gnews_api_key=None)  # type: ignore[arg-type]

        stats = await run_ingestion(settings, EMBEDDER)

        assert stats.gnews_calls == 0
        sources = (await session.execute(select(Source))).scalars().all()
        assert sources == []

    async def test_a_configured_key_backfills_and_attributes_the_source(
        self,
        database: str,
        session: AsyncSession,
        app_engine: None,
        backfill_topics: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        entry = ParsedEntry(
            url_canonical="https://example.com/backfilled-story",
            title="A backfilled headline",
            snippet="From GNews.",
            image_url=None,
            author_name=None,
            language="es",
            published_at=datetime.now(UTC),
            source_name="Example Daily",
            source_url="https://example.com",
        )
        monkeypatch.setattr(
            "justnews_ingestion.pipeline.gnews.top_headlines",
            AsyncMock(return_value=[entry]),
        )
        settings = Settings(  # type: ignore[call-arg]
            database_url=database,
            gnews_api_key="test-key",
            ingest_max_gnews_calls_per_run=1,
        )

        stats = await run_ingestion(settings, EMBEDDER)

        assert stats.gnews_calls == 1
        assert stats.articles_new == 1

        source = (
            await session.execute(select(Source).where(Source.slug == "example-daily"))
        ).scalar_one()
        assert source.name == "Example Daily"
        assert source.homepage_url == "https://example.com"

        article = (
            await session.execute(select(Article).where(Article.source_id == source.id))
        ).scalar_one()
        assert article.title == "A backfilled headline"
        assert article.feed_id is None

    async def test_a_missing_source_name_is_skipped_rather_than_fabricated(
        self,
        database: str,
        session: AsyncSession,
        app_engine: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        entry = ParsedEntry(
            url_canonical="https://example.com/no-source",
            title="No publisher attached",
            snippet=None,
            image_url=None,
            author_name=None,
            language="en",
            published_at=datetime.now(UTC),
            source_name=None,
            source_url=None,
        )
        monkeypatch.setattr(
            "justnews_ingestion.pipeline.gnews.top_headlines",
            AsyncMock(return_value=[entry]),
        )
        settings = Settings(database_url=database, gnews_api_key="test-key")  # type: ignore[call-arg]

        stats = await run_ingestion(settings, EMBEDDER)

        assert stats.gnews_calls == 1
        assert stats.articles_new == 0


class TestGnewsTopicAttribution:
    async def test_the_requested_category_becomes_the_articles_topic(
        self,
        database: str,
        session: AsyncSession,
        app_engine: None,
        backfill_topics: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The whole point of topic backfill: a Spanish health article arrives
        already knowing it is about health, which is precisely what the general
        feeds could never tell us."""
        requested: dict[str, str] = {}

        async def fake_top_headlines(*_args: object, **kwargs: object) -> list[ParsedEntry]:
            requested["language"] = str(kwargs["language"])
            requested["category"] = str(kwargs["category"])
            return [
                ParsedEntry(
                    url_canonical="https://example.com/salud",
                    title="Un titular sobre salud",
                    snippet="Desde GNews.",
                    image_url=None,
                    author_name=None,
                    language="es",
                    published_at=datetime.now(UTC),
                    source_name="Example Salud",
                    source_url="https://example.com",
                )
            ]

        monkeypatch.setattr("justnews_ingestion.pipeline.gnews.top_headlines", fake_top_headlines)
        settings = Settings(  # type: ignore[call-arg]
            database_url=database, gnews_api_key="test-key", ingest_max_gnews_calls_per_run=1
        )

        stats = await run_ingestion(settings, EMBEDDER)

        assert stats.errors == [], stats.errors
        assert stats.gnews_calls == 1
        assert requested["category"] in set(gnews.GNEWS_CATEGORY_BY_TOPIC.values())

        article = (
            await session.execute(select(Article).where(Article.title == "Un titular sobre salud"))
        ).scalar_one()
        topic = (
            await session.execute(select(ArticleTopic).where(ArticleTopic.article_id == article.id))
        ).scalar_one()
        # Provenance is recorded distinctly from a feed's own section: equally
        # confident, but not the same evidence.
        assert topic.assigned_by == "gnews_category"
        assert gnews.GNEWS_CATEGORY_BY_TOPIC[topic.topic_id] == requested["category"]
