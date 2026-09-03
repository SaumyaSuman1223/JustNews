"""Integration tests for the topics list."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.factories import make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import TopicLabel


class TestListTopics:
    async def test_lists_top_level_topics_with_labels(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:01000000", slug="arts")
        session.add(TopicLabel(topic_id=topic.id, language="es", label="Arte"))
        await session.commit()

        response = await client.get("/v1/topics?language=es")
        assert response.status_code == 200
        body = response.json()
        assert {t["id"]: t["label"] for t in body}[topic.id] == "Arte"

    async def test_falls_back_to_english_then_slug(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:02000000", slug="crime-law")
        session.add(TopicLabel(topic_id=topic.id, language="en", label="Crime and law"))
        await session.commit()

        response = await client.get("/v1/topics?language=fr")
        body = {t["id"]: t["label"] for t in response.json()}
        assert body[topic.id] == "Crime and law"

    async def test_rejects_an_invalid_language(self, client: AsyncClient) -> None:
        response = await client.get("/v1/topics?language=zzzz9")
        assert response.status_code == 422

    async def test_excludes_inactive_topics(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:03000000", slug="retired")
        topic.active = False
        await session.commit()

        response = await client.get("/v1/topics")
        assert topic.id not in {t["id"] for t in response.json()}
