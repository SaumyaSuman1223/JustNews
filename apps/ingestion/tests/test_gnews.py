"""GNews client: response parsing (no network) and thin-language ranking (real DB)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.errors import QuotaExceededError, UpstreamError
from justnews_core.language import LAUNCH_LANGUAGES
from justnews_core.settings import Settings
from justnews_ingestion import gnews

SETTINGS = Settings(gnews_api_key="test-key")

GNEWS_PAYLOAD = {
    "articles": [
        {
            "title": "Central bank holds rates steady",
            "description": "The decision was widely expected.",
            "url": "https://example.com/news/rates",
            "image": "https://example.com/img.jpg",
            "publishedAt": "2026-08-31T09:00:00Z",
            "source": {"name": "Example Times", "url": "https://example.com"},
        },
        {
            # Missing url - must be skipped, not raise.
            "title": "No link here",
            "source": {"name": "Nobody"},
        },
    ]
}


def _mock_client(payload: object, *, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=json.dumps(payload))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestTopHeadlines:
    async def test_parses_articles_and_captures_source_attribution(
        self, session: AsyncSession
    ) -> None:
        async with _mock_client(GNEWS_PAYLOAD) as client:
            entries = await gnews.top_headlines(session, client, SETTINGS, language="en")

        assert len(entries) == 1
        entry = entries[0]
        assert entry.title == "Central bank holds rates steady"
        assert entry.source_name == "Example Times"
        assert entry.source_url == "https://example.com"

    async def test_a_missing_api_key_raises_before_any_call(self, session: AsyncSession) -> None:
        settings = Settings(gnews_api_key=None)
        async with _mock_client(GNEWS_PAYLOAD) as client:
            with pytest.raises(UpstreamError):
                await gnews.top_headlines(session, client, settings, language="en")

    async def test_exhausted_daily_budget_raises_quota_exceeded(
        self, session: AsyncSession
    ) -> None:
        settings = Settings(gnews_api_key="test-key", ingest_max_gnews_calls_per_day=1)
        async with _mock_client(GNEWS_PAYLOAD) as client:
            await gnews.top_headlines(session, client, settings, language="en")
            with pytest.raises(QuotaExceededError):
                await gnews.top_headlines(session, client, settings, language="hi")

    async def test_garbage_response_yields_no_entries_rather_than_raising(
        self, session: AsyncSession
    ) -> None:
        async with _mock_client({"unexpected": "shape"}) as client:
            entries = await gnews.top_headlines(session, client, SETTINGS, language="en")
        assert entries == []


class TestThinLanguages:
    async def test_an_unseeded_language_ranks_first(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, language="en", minutes_ago=5)
        await session.flush()

        ranked = await gnews.thin_languages(
            session, since=datetime.now(UTC) - timedelta(hours=24), limit=3
        )

        assert ranked[0] != "en"
        assert set(ranked).issubset(set(LAUNCH_LANGUAGES))

    async def test_a_language_with_more_recent_articles_ranks_lower(
        self, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        for _ in range(5):
            await make_article(session, source, language="es", minutes_ago=5)
        await make_article(session, source, language="hi", minutes_ago=5)
        await session.flush()

        ranked = await gnews.thin_languages(
            session, since=datetime.now(UTC) - timedelta(hours=24), limit=len(LAUNCH_LANGUAGES)
        )

        assert ranked.index("hi") < ranked.index("es")

    async def test_articles_outside_the_window_do_not_count(self, session: AsyncSession) -> None:
        source = await make_source(session)
        for _ in range(5):
            await make_article(session, source, language="es", minutes_ago=60 * 48)
        await session.flush()

        ranked = await gnews.thin_languages(
            session, since=datetime.now(UTC) - timedelta(hours=24), limit=1
        )

        # "es" has articles, but all outside the window, so it counts as zero
        # exactly like every other untouched language - the tie goes to
        # whichever comes first in LAUNCH_LANGUAGES, which is "en".
        assert ranked == [LAUNCH_LANGUAGES[0]]
