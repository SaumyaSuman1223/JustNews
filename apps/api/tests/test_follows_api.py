"""Integration tests for followed topics."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.factories import make_topic
from sqlalchemy.ext.asyncio import AsyncSession


class TestFollows:
    async def test_follows_a_topic(self, client: AsyncClient, session: AsyncSession) -> None:
        topic = await make_topic(session)
        await session.commit()

        token = make_access_token()
        response = await client.post(
            "/v1/follows",
            json={"topic_id": topic.id},
            headers={"authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["topic_id"] == topic.id

    async def test_following_an_unknown_topic_is_404(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.post(
            "/v1/follows",
            json={"topic_id": "medtop:does-not-exist"},
            headers={"authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_unfollow_then_list_is_empty(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session)
        await session.commit()

        headers = {"authorization": f"Bearer {make_access_token()}"}
        await client.post("/v1/follows", json={"topic_id": topic.id}, headers=headers)
        delete = await client.delete(f"/v1/follows/{topic.id}", headers=headers)
        assert delete.status_code == 204

        listed = await client.get("/v1/follows", headers=headers)
        assert listed.json() == []

    async def test_unfollowing_something_never_followed_is_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session)
        await session.commit()
        token = make_access_token()
        response = await client.delete(
            f"/v1/follows/{topic.id}", headers={"authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
