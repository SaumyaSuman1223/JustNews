"""Integration tests for full text search."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession


class TestSearch:
    async def test_matches_a_word_in_the_title(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Earthquake strikes the capital")
        await make_article(session, source, title="Markets close higher")
        await session.commit()

        # A single requested language picks that language's search config, so
        # stemming matches how the article was indexed (see repositories.
        # content.search_articles); with none requested it falls back to
        # "simple" (no stemming), which only matches literal tokens.
        body = (await client.get("/v1/search?q=earthquake&languages=en")).json()
        assert [item["title"] for item in body["items"]] == ["Earthquake strikes the capital"]

    async def test_no_match_is_an_empty_page_not_an_error(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/search?q=nonexistentword")).json()
        assert body == {"items": [], "next_cursor": None}

    async def test_rejects_a_too_short_query(self, client: AsyncClient) -> None:
        response = await client.get("/v1/search?q=a")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_language_filter_applies(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Elección en la capital", language="es")
        await make_article(session, source, title="Election in the capital", language="en")
        await session.commit()

        body = (await client.get("/v1/search?q=capital&languages=es")).json()
        assert [item["language"] for item in body["items"]] == ["es"]
