"""Integration tests for full text search."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic


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
        assert body == {"items": [], "next_cursor": None, "total": 0}

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

    async def test_topic_filter_applies(self, client: AsyncClient, session: AsyncSession) -> None:
        """Searching within a topic must agree with browsing that topic."""
        topic = await make_topic(session, topic_id="medtop:11000000", slug="politics")
        source = await make_source(session)
        tagged = await make_article(session, source, title="Election in the capital")
        await make_article(session, source, title="Election of a club captain")
        session.add(ArticleTopic(article_id=tagged.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        unfiltered = (await client.get("/v1/search?q=election&languages=en")).json()
        assert len(unfiltered["items"]) == 2

        body = (await client.get(f"/v1/search?q=election&languages=en&topic={topic.id}")).json()
        assert [item["title"] for item in body["items"]] == ["Election in the capital"]

    async def test_an_unknown_topic_matches_nothing_rather_than_everything(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Election in the capital")
        await session.commit()

        body = (await client.get("/v1/search?q=election&languages=en&topic=medtop:00000000")).json()
        assert body["items"] == []

    async def test_source_filter_applies(self, client: AsyncClient, session: AsyncSession) -> None:
        """Audit §27's source filter: narrows to one publisher's own results."""
        wanted = await make_source(session, slug="wanted-wire", name="Wanted Wire")
        other = await make_source(session, slug="other-wire", name="Other Wire")
        await make_article(session, wanted, title="Election in the capital")
        await make_article(session, other, title="Election of a club captain")
        await session.commit()

        unfiltered = (await client.get("/v1/search?q=election&languages=en")).json()
        assert len(unfiltered["items"]) == 2

        body = (await client.get(f"/v1/search?q=election&languages=en&source={wanted.id}")).json()
        assert [item["title"] for item in body["items"]] == ["Election in the capital"]

    async def test_an_unknown_source_matches_nothing_rather_than_everything(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Election in the capital")
        await session.commit()

        body = (await client.get("/v1/search?q=election&languages=en&source=999999")).json()
        assert body["items"] == []


class TestSearchTotal:
    """Audit §28's results count.

    The number has to describe the whole result set, not the page - and it has
    to be counted with the same predicate the listing uses, or the heading
    says one thing and the list shows another.
    """

    async def test_counts_beyond_the_first_page(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        for index in range(5):
            await make_article(session, source, title=f"Election result number {index}")
        await session.commit()

        body = (await client.get("/v1/search?q=election&languages=en&page_size=2")).json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    async def test_the_count_respects_every_filter(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:11000000", slug="politics")
        source = await make_source(session)
        tagged = await make_article(session, source, title="Election in the capital")
        await make_article(session, source, title="Election of a club captain")
        await make_article(session, source, title="Elección en la capital", language="es")
        session.add(ArticleTopic(article_id=tagged.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        unfiltered = (await client.get("/v1/search?q=election&languages=en")).json()
        assert unfiltered["total"] == 2

        filtered = (await client.get(f"/v1/search?q=election&languages=en&topic={topic.id}")).json()
        assert filtered["total"] == 1
        assert len(filtered["items"]) == filtered["total"]

    async def test_a_later_page_does_not_recount(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # The count is the same on every page by construction, so paying for
        # it again buys nothing. Absent rather than wrong: the client has it
        # from the page it started on.
        source = await make_source(session)
        for index in range(3):
            await make_article(session, source, title=f"Election result number {index}")
        await session.commit()

        first = (await client.get("/v1/search?q=election&languages=en&page_size=1")).json()
        assert first["total"] == 3
        assert first["next_cursor"] is not None

        second = (
            await client.get(
                f"/v1/search?q=election&languages=en&page_size=1&cursor={first['next_cursor']}"
            )
        ).json()
        assert second["total"] is None
