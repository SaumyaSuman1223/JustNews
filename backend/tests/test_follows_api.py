"""Integration tests for followed topics."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic


class TestFollows:
    async def test_follows_a_topic(self, client: AsyncClient, session: AsyncSession) -> None:
        topic = await make_topic(session)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.post("/v1/follows", json={"topic_id": topic.id}, headers=headers)
        assert response.status_code == 201
        assert response.json()["topic_id"] == topic.id

    async def test_following_an_unknown_topic_is_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/follows", json={"topic_id": "medtop:does-not-exist"}, headers=headers
        )
        assert response.status_code == 404

    async def test_unfollow_then_list_is_empty(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session)
        await session.commit()

        headers = await make_beta_headers(session)
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
        headers = await make_beta_headers(session)
        response = await client.delete(f"/v1/follows/{topic.id}", headers=headers)
        assert response.status_code == 404


class TestExplorationDeckFollowBridge:
    """The exploration deck's compatibility bridge (services.exploration_deck
    .record_deck_engagement): strong-signal deck engagement with enough
    distinct articles in one topic creates a real follow, without the reader
    ever checking a box - see that module's docstring for why this exists."""

    async def test_two_distinct_clicks_in_one_topic_create_a_follow(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000020", slug="bridge-two-clicks")
        first = await make_article(session, source, title="First")
        second = await make_article(session, source, title="Second")
        session.add(ArticleTopic(article_id=first.id, topic_id=topic.id, is_primary=True))
        session.add(ArticleTopic(article_id=second.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        for article in (first, second):
            response = await client.post(
                "/v1/history",
                json={"article_id": article.id, "surface": "onboarding", "topic_id": topic.id},
                headers=headers,
            )
            assert response.status_code == 204

        follows = (await client.get("/v1/follows", headers=headers)).json()
        assert [f["topic_id"] for f in follows] == [topic.id]

    async def test_a_single_click_does_not_create_a_follow(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000021", slug="bridge-one-click")
        article = await make_article(session, source)
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/history",
            json={"article_id": article.id, "surface": "onboarding", "topic_id": topic.id},
            headers=headers,
        )

        follows = (await client.get("/v1/follows", headers=headers)).json()
        assert follows == []

    async def test_not_interested_never_creates_a_follow(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000022", slug="bridge-not-interested")
        first = await make_article(session, source, title="First")
        second = await make_article(session, source, title="Second")
        session.add(ArticleTopic(article_id=first.id, topic_id=topic.id, is_primary=True))
        session.add(ArticleTopic(article_id=second.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        # report_not_interested has no topic_id parameter at all - the
        # bridge cannot trigger from it by construction. Two marks, to rule
        # out anything that might coincidentally cross the threshold.
        for article in (first, second):
            await client.post(
                "/v1/not-interested",
                json={"article_id": article.id, "surface": "onboarding"},
                headers=headers,
            )

        follows = (await client.get("/v1/follows", headers=headers)).json()
        assert follows == []

    async def test_crossing_the_threshold_again_does_not_double_write(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000023", slug="bridge-idempotent")
        articles = [await make_article(session, source, title=f"A{i}") for i in range(3)]
        for article in articles:
            session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        for article in articles:
            response = await client.post(
                "/v1/history",
                json={"article_id": article.id, "surface": "onboarding", "topic_id": topic.id},
                headers=headers,
            )
            assert response.status_code == 204

        follows = (await client.get("/v1/follows", headers=headers)).json()
        assert [f["topic_id"] for f in follows] == [topic.id]
