"""Integration tests for feed card reasons (fifth pass F7): every reason is a
factor the heuristic ranker actually applied, never an invented one."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.feed import CHRONOLOGICAL_POLICY, HEURISTIC_POLICY
from justnews_core.models import ArticleTopic, FeatureFlag


async def _no_exploration(session: AsyncSession) -> None:
    # Exploration slots carry their own reason; off here so every card on the
    # page is one the ranker placed.
    session.add(FeatureFlag(key="exploration_deck", enabled=False, description="off for test"))


class TestFeedReasons:
    async def test_a_followed_topic_is_named_as_the_reason(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _no_exploration(session)
        topic = await make_topic(session, topic_id="medtop:20000040", slug="reason-topic")
        source = await make_source(session)
        tagged = await make_article(session, source, title="About the followed topic")
        session.add(ArticleTopic(article_id=tagged.id, topic_id=topic.id, is_primary=True))
        await make_article(session, source, title="Something else")
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        await client.post("/v1/follows", json={"topic_id": topic.id}, headers=headers)

        items = (await client.get("/v1/feed", headers=headers)).json()["items"]
        by_title = {item["article"]["title"]: item["reason"] for item in items}
        assert by_title["About the followed topic"] == {
            "kind": "followed_topic",
            "topic_id": topic.id,
        }
        # Placed on recency alone - nothing to explain, so nothing claimed.
        assert by_title["Something else"] is None

    async def test_the_chronological_control_claims_no_reasons(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Plain")
        await session.commit()

        user_id = find_user_id_for_policy(CHRONOLOGICAL_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        items = (await client.get("/v1/feed", headers=headers)).json()["items"]
        assert items and all(item["reason"] is None for item in items)
