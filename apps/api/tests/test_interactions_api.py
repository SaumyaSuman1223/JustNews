"""Integration tests for click/history reporting and not-interested."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession


class TestReportClick:
    async def test_records_and_lists_a_click(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Read me")
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        report = await client.post(
            "/v1/history",
            json={"article_id": article.id, "surface": "feed", "position": 0},
            headers=headers,
        )
        assert report.status_code == 204

        history = (await client.get("/v1/history", headers=headers)).json()
        assert [item["article"]["title"] for item in history["items"]] == ["Read me"]

    async def test_unknown_article_is_404(self, client: AsyncClient) -> None:
        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.post(
            "/v1/history",
            json={"article_id": 999999, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_invalid_surface_is_rejected(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.post(
            "/v1/history",
            json={"article_id": article.id, "surface": "homepage"},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_a_reader_never_sees_another_readers_history(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        alice = {"authorization": f"Bearer {make_access_token()}"}
        bob = {"authorization": f"Bearer {make_access_token()}"}
        await client.post(
            "/v1/history", json={"article_id": article.id, "surface": "feed"}, headers=alice
        )

        bob_history = (await client.get("/v1/history", headers=bob)).json()
        assert bob_history["items"] == []


class TestNotInterested:
    async def test_removes_the_article_from_a_later_feed_page(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.post(
            "/v1/not-interested",
            json={"article_id": article.id, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 204

    async def test_unknown_article_is_404(self, client: AsyncClient) -> None:
        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.post(
            "/v1/not-interested",
            json={"article_id": 999999, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 404
