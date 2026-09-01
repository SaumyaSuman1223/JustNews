"""Integration tests for data export and account deletion (compliance)."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession


class TestExport:
    async def test_export_includes_saves_follows_and_history(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        topic = await make_topic(session)
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post("/v1/saves", json={"article_id": article.id}, headers=headers)
        await client.post("/v1/follows", json={"topic_id": topic.id}, headers=headers)
        await client.post(
            "/v1/history", json={"article_id": article.id, "surface": "feed"}, headers=headers
        )

        export = await client.get("/v1/me/export", headers=headers)
        assert export.status_code == 200
        body = export.json()
        assert [row["article_id"] for row in body["saves"]] == [article.id]
        assert [row["topic_id"] for row in body["follows"]] == [topic.id]
        assert [row["article_id"] for row in body["history"]] == [article.id]

    async def test_export_requires_auth(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/me/export")).status_code == 401


class TestAccountDeletion:
    async def test_deleting_the_account_removes_saves_and_follows(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post("/v1/saves", json={"article_id": article.id}, headers=headers)

        delete = await client.delete("/v1/me", headers=headers)
        assert delete.status_code == 204

        # A fresh call re-creates the profile lazily, with no memory of the
        # deleted state - proof the account genuinely started over.
        again = await client.get("/v1/me", headers=headers)
        assert again.json()["has_beta_access"] is False

    async def test_deletion_requires_auth(self, client: AsyncClient) -> None:
        assert (await client.delete("/v1/me")).status_code == 401
