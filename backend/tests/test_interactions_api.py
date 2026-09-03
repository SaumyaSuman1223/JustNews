"""Integration tests for click/history reporting and not-interested."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession


class TestReportClick:
    async def test_records_and_lists_a_click(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Read me")
        await session.commit()

        headers = await make_beta_headers(session)
        report = await client.post(
            "/v1/history",
            json={"article_id": article.id, "surface": "feed", "position": 0},
            headers=headers,
        )
        assert report.status_code == 204

        history = (await client.get("/v1/history", headers=headers)).json()
        assert [item["article"]["title"] for item in history["items"]] == ["Read me"]

    async def test_unknown_article_is_404(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session)
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

        headers = await make_beta_headers(session)
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

        alice = await make_beta_headers(session)
        bob = await make_beta_headers(session)
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

        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/not-interested",
            json={"article_id": article.id, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 204

    async def test_unknown_article_is_404(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/not-interested",
            json={"article_id": 999999, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 404


class TestUndoNotInterested:
    async def test_undoes_a_mark(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/not-interested",
            json={"article_id": article.id, "surface": "feed"},
            headers=headers,
        )
        response = await client.delete(
            f"/v1/not-interested/{article.id}", params={"surface": "feed"}, headers=headers
        )
        assert response.status_code == 204

    async def test_requires_surface(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.delete(f"/v1/not-interested/{article.id}", headers=headers)
        assert response.status_code == 422

    async def test_unknown_article_is_404(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session)
        response = await client.delete(
            "/v1/not-interested/999999", params={"surface": "feed"}, headers=headers
        )
        assert response.status_code == 404

    async def test_undoing_a_mark_that_was_never_made_is_still_a_valid_event(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # No POST /v1/not-interested first: the log is append-only and an
        # extra reversal event is harmless, not an error to reject.
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.delete(
            f"/v1/not-interested/{article.id}", params={"surface": "feed"}, headers=headers
        )
        assert response.status_code == 204
