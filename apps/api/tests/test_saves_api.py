"""Integration tests for bookmarks."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession


class TestCreateSave:
    async def test_saves_an_article(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Save me")
        await session.commit()

        token = make_access_token()
        response = await client.post(
            "/v1/saves",
            json={"article_id": article.id},
            headers={"authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["article"]["id"] == article.id

    async def test_saving_twice_is_not_an_error(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        first = await client.post("/v1/saves", json={"article_id": article.id}, headers=headers)
        second = await client.post("/v1/saves", json={"article_id": article.id}, headers=headers)
        assert first.status_code == second.status_code == 201

    async def test_unknown_article_is_404(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.post(
            "/v1/saves", json={"article_id": 999999}, headers={"authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


class TestDeleteSave:
    async def test_unsaves_an_article(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        await client.post("/v1/saves", json={"article_id": article.id}, headers=headers)
        delete = await client.delete(f"/v1/saves/{article.id}", headers=headers)
        assert delete.status_code == 204

        listed = await client.get("/v1/saves", headers=headers)
        assert listed.json()["items"] == []

    async def test_unsaving_something_never_saved_is_404(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.delete("/v1/saves/1", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 404


class TestListSaves:
    async def test_lists_newest_first(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        first = await make_article(session, source, title="First")
        second = await make_article(session, source, title="Second")
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        await client.post("/v1/saves", json={"article_id": first.id}, headers=headers)
        await client.post("/v1/saves", json={"article_id": second.id}, headers=headers)

        body = (await client.get("/v1/saves", headers=headers)).json()
        titles = [item["article"]["title"] for item in body["items"]]
        assert titles == ["Second", "First"]

    async def test_a_reader_never_sees_another_readers_saves(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        alice = {"authorization": f"Bearer {make_access_token()}"}
        bob = {"authorization": f"Bearer {make_access_token()}"}
        await client.post("/v1/saves", json={"article_id": article.id}, headers=alice)

        bob_saves = (await client.get("/v1/saves", headers=bob)).json()
        assert bob_saves["items"] == []
