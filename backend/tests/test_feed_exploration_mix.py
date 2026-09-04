"""Integration tests for the Stage 7 exploration mix woven into the
heuristic feed policy's own pages - kept separate from test_ranking.py so
that file's diff for this change stays small."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.feed import (
    CHRONOLOGICAL_POLICY,
    HEURISTIC_EXPLORE_MIX_POLICY,
    HEURISTIC_POLICY,
)
from justnews_core.db import set_current_user
from justnews_core.models import ArticleTopic, FeatureFlag, Impression


async def _seed_mainstream(session: AsyncSession, source, count: int) -> None:
    for i in range(count):
        await make_article(session, source, title=f"Mainstream {i}", minutes_ago=i)


class TestFeedExplorationMix:
    async def test_the_trailing_slots_can_surface_an_article_ranking_would_never_show(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await _seed_mainstream(session, source, 25)

        topic = await make_topic(session, topic_id="medtop:20000030", slug="mix-topic")
        buried = []
        for i in range(3):
            # Ancient by this ranker's recency half-life (18h) - scores
            # near zero, so plain ranking would never place these in the
            # top 20 regardless of anything else about them.
            article = await make_article(session, source, title=f"Buried {i}", minutes_ago=100_000)
            session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
            buried.append(article)
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed?page_size=20", headers=headers)
        assert response.status_code == 200

        titles = [item["article"]["title"] for item in response.json()["items"]]
        buried_titles = {a.title for a in buried}
        assert buried_titles & set(titles), "the exploratory tail never surfaced a buried article"

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(row.ranking_policy == HEURISTIC_EXPLORE_MIX_POLICY for row in rows)

    async def test_flag_off_never_mixes_and_keeps_the_plain_policy_name(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        session.add(
            FeatureFlag(key="exploration_deck", enabled=False, description="off for this test")
        )
        await session.commit()

        source = await make_source(session)
        await _seed_mainstream(session, source, 25)
        topic = await make_topic(session, topic_id="medtop:20000031", slug="mix-topic-off")
        buried = await make_article(session, source, title="Buried off", minutes_ago=100_000)
        session.add(ArticleTopic(article_id=buried.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed?page_size=20", headers=headers)
        assert response.status_code == 200

        titles = [item["article"]["title"] for item in response.json()["items"]]
        assert "Buried off" not in titles

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(row.ranking_policy == HEURISTIC_POLICY for row in rows)

    async def test_chronological_policy_is_never_mixed(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await _seed_mainstream(session, source, 25)
        topic = await make_topic(session, topic_id="medtop:20000032", slug="mix-topic-chrono")
        buried = await make_article(session, source, title="Buried chrono", minutes_ago=100_000)
        session.add(ArticleTopic(article_id=buried.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        user_id = find_user_id_for_policy(CHRONOLOGICAL_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed?page_size=20", headers=headers)
        assert response.status_code == 200

        titles = [item["article"]["title"] for item in response.json()["items"]]
        assert "Buried chrono" not in titles

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(row.ranking_policy == CHRONOLOGICAL_POLICY for row in rows)

    async def test_exploration_slots_still_respect_not_interested_exclusion(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await _seed_mainstream(session, source, 25)
        topic = await make_topic(session, topic_id="medtop:20000033", slug="mix-topic-excl")
        excluded_article = await make_article(
            session, source, title="Buried excluded", minutes_ago=100_000
        )
        session.add(
            ArticleTopic(article_id=excluded_article.id, topic_id=topic.id, is_primary=True)
        )
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        await client.post(
            "/v1/not-interested",
            json={"article_id": excluded_article.id, "surface": "feed"},
            headers=headers,
        )

        response = await client.get("/v1/feed?page_size=20", headers=headers)
        titles = [item["article"]["title"] for item in response.json()["items"]]
        assert "Buried excluded" not in titles
