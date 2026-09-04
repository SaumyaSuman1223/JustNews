"""Integration tests for My Desk's topic-scoped reads: overview, timeline
(story clusters) and related topics."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, StoryCluster


class TestTopicOverview:
    async def test_counts_live_articles_sources_and_stories(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source_a = await make_source(session, slug="overview-a")
        source_b = await make_source(session, slug="overview-b")
        topic = await make_topic(session, topic_id="medtop:40000001", slug="overview-topic")
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="Overview story",
            first_seen_at=now,
            last_seen_at=now,
            article_count=1,
            source_count=1,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()

        one = await make_article(session, source_a, title="One")
        two = await make_article(session, source_b, title="Two")
        two.story_cluster_id = cluster.id
        session.add_all(
            [
                ArticleTopic(article_id=one.id, topic_id=topic.id, is_primary=True),
                ArticleTopic(article_id=two.id, topic_id=topic.id, is_primary=True),
            ]
        )
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/overview")
        assert response.status_code == 200
        body = response.json()
        assert body == {"articles": 2, "sources": 2, "stories": 1}

    async def test_a_removed_article_does_not_count(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:40000002", slug="overview-removed")
        article = await make_article(session, source)
        article.removed_at = datetime.now(UTC)
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/overview")
        assert response.json() == {"articles": 0, "sources": 0, "stories": 0}

    async def test_unknown_topic_is_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/topics/medtop:does-not-exist/overview")
        assert response.status_code == 404


class TestTopicStories:
    async def test_returns_clusters_tagged_with_this_topic_most_recent_first(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:40000003", slug="timeline-topic")
        older = datetime(2026, 1, 1, tzinfo=UTC)
        newer = datetime(2026, 2, 1, tzinfo=UTC)

        old_cluster = StoryCluster(
            title="Older story",
            first_seen_at=older,
            last_seen_at=older,
            article_count=1,
            source_count=1,
            language_count=1,
        )
        new_cluster = StoryCluster(
            title="Newer story",
            first_seen_at=newer,
            last_seen_at=newer,
            article_count=1,
            source_count=1,
            language_count=1,
        )
        session.add_all([old_cluster, new_cluster])
        await session.flush()

        old_article = await make_article(session, source, title="Old")
        new_article = await make_article(session, source, title="New")
        old_article.story_cluster_id = old_cluster.id
        new_article.story_cluster_id = new_cluster.id
        session.add_all(
            [
                ArticleTopic(article_id=old_article.id, topic_id=topic.id, is_primary=True),
                ArticleTopic(article_id=new_article.id, topic_id=topic.id, is_primary=True),
            ]
        )
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/stories")
        assert response.status_code == 200
        body = response.json()
        assert [s["id"] for s in body] == [new_cluster.id, old_cluster.id]
        assert body[0]["first_seen_at"] is not None

    async def test_a_story_with_no_articles_in_this_topic_is_excluded(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:40000004", slug="timeline-exclude")
        other_topic = await make_topic(session, topic_id="medtop:40000005", slug="timeline-other")
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="Unrelated story",
            first_seen_at=now,
            last_seen_at=now,
            article_count=1,
            source_count=1,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()
        article = await make_article(session, source)
        article.story_cluster_id = cluster.id
        session.add(ArticleTopic(article_id=article.id, topic_id=other_topic.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/stories")
        assert response.json() == []


class TestRelatedTopics:
    async def test_orders_by_shared_article_count(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        main = await make_topic(session, topic_id="medtop:40000006", slug="related-main")
        popular = await make_topic(session, topic_id="medtop:40000007", slug="related-popular")
        rare = await make_topic(session, topic_id="medtop:40000008", slug="related-rare")

        shared_twice = [await make_article(session, source, title=f"Popular {i}") for i in range(2)]
        shared_once = await make_article(session, source, title="Rare")
        for article in shared_twice:
            session.add(ArticleTopic(article_id=article.id, topic_id=main.id, is_primary=True))
            session.add(ArticleTopic(article_id=article.id, topic_id=popular.id, is_primary=True))
        session.add(ArticleTopic(article_id=shared_once.id, topic_id=main.id, is_primary=True))
        session.add(ArticleTopic(article_id=shared_once.id, topic_id=rare.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/topics/{main.id}/related")
        assert response.status_code == 200
        body = response.json()
        assert [t["id"] for t in body] == [popular.id, rare.id]
        assert body[0]["article_count"] == 2

    async def test_a_topic_is_never_related_to_itself(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:40000009", slug="related-self")
        article = await make_article(session, source)
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/topics/{topic.id}/related")
        assert response.json() == []

    async def test_unknown_topic_is_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/topics/medtop:does-not-exist/related")
        assert response.status_code == 404
