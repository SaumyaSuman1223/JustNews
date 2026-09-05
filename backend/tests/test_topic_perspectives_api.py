"""Integration tests for GET /v1/topics/{id}/perspectives (ADR 0013)."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article, ArticleTopic, Source, StoryCluster, Topic


async def _clustered_article(
    session: AsyncSession, source: Source, topic: Topic, *, title: str
) -> Article:
    now = datetime.now(UTC)
    cluster = StoryCluster(
        title=title,
        first_seen_at=now,
        last_seen_at=now,
        article_count=1,
        source_count=1,
        language_count=1,
    )
    session.add(cluster)
    await session.flush()
    article = await make_article(session, source, title=title)
    article.story_cluster_id = cluster.id
    session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
    return article
    return article


class TestTopicPerspectives:
    async def test_groups_by_role_excluding_wire_and_unroled(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:50000001", slug="perspectives-topic")
        industry = await make_source(session, slug="persp-industry", source_role="industry")
        wire = await make_source(session, slug="persp-wire", source_role="wire")
        unroled = await make_source(session, slug="persp-unroled")

        await _clustered_article(session, industry, topic, title="Industry take")
        await _clustered_article(session, wire, topic, title="Wire report")
        await _clustered_article(session, unroled, topic, title="Unroled piece")
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/perspectives")
        assert response.status_code == 200
        body = response.json()
        assert [g["role"] for g in body] == ["industry"]
        assert body[0]["sources"][0]["slug"] == "persp-industry"
        assert body[0]["sources"][0]["homepage_url"] == "https://persp-industry.example"

    async def test_an_unclustered_article_does_not_contribute(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:50000002", slug="perspectives-loose")
        source = await make_source(session, slug="persp-loose", source_role="government")
        article = await make_article(session, source, title="Not yet clustered")
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/perspectives")
        assert response.json() == []

    async def test_no_roled_coverage_is_an_empty_list_not_an_error(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:50000003", slug="perspectives-empty")
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/perspectives")
        assert response.status_code == 200
        assert response.json() == []

    async def test_unknown_topic_is_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/topics/medtop:does-not-exist/perspectives")
        assert response.status_code == 404

    async def test_two_sources_in_one_role_both_appear(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session, topic_id="medtop:50000004", slug="perspectives-multi")
        first = await make_source(session, slug="persp-multi-a", source_role="academic")
        second = await make_source(session, slug="persp-multi-b", source_role="academic")

        await _clustered_article(session, first, topic, title="Study one")
        await _clustered_article(session, second, topic, title="Study two")
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/perspectives")
        body = response.json()
        assert len(body) == 1
        assert body[0]["role"] == "academic"
        assert body[0]["article_count"] == 2
        assert {s["slug"] for s in body[0]["sources"]} == {"persp-multi-a", "persp-multi-b"}
