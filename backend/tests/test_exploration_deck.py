"""Integration tests for the Stage 7 exploration deck: stratified sampling,
per-topic caps, honest propensity logging, and the kill switch."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, FeatureFlag, Impression


async def _tag(
    session: AsyncSession, *, article_id: int, topic_id: str, is_primary: bool = True
) -> None:
    session.add(ArticleTopic(article_id=article_id, topic_id=topic_id, is_primary=is_primary))


class TestExplorationDeck:
    async def test_per_topic_cap_is_honored(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000010", slug="topic-cap")
        for i in range(10):
            article = await make_article(session, source, title=f"Cap {i}")
            await _tag(session, article_id=article.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)

        assert response.status_code == 200
        cards = response.json()["cards"]
        # Only one topic exists in this test's corpus, so the whole deck
        # comes from it - the cap (3) is the only thing limiting it, not the
        # deck size (20).
        assert 0 < len(cards) <= 3

    async def test_language_filter_is_respected(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000011", slug="topic-lang")
        en_article = await make_article(session, source, title="English", language="en")
        es_article = await make_article(session, source, title="Spanish", language="es")
        await _tag(session, article_id=en_article.id, topic_id=topic.id)
        await _tag(session, article_id=es_article.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.get("/v1/exploration-deck?locale=en&languages=es", headers=headers)

        assert response.status_code == 200
        titles = [card["article"]["title"] for card in response.json()["cards"]]
        assert titles == ["Spanish"]

    async def test_deck_degrades_gracefully_on_a_thin_corpus(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000012", slug="topic-thin")
        article = await make_article(session, source, title="Only one")
        await _tag(session, article_id=article.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)

        assert response.status_code == 200
        assert len(response.json()["cards"]) == 1

    async def test_impressions_are_logged_with_a_real_propensity(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000013", slug="topic-propensity")
        # More candidates than the per-topic cap (3) draws - with the pool
        # never exhausted down to its last item, every draw's propensity is
        # a genuine fraction, not the certainty a final, forced pick would
        # have.
        for i in range(10):
            article = await make_article(session, source, title=f"Propensity {i}")
            await _tag(session, article_id=article.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)
        assert response.status_code == 200
        cards = response.json()["cards"]
        assert all(card["impression_id"] is not None for card in cards)

        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows
        for row in rows:
            assert row.surface == "onboarding"
            assert row.ranking_policy == "exploration_deck_v1"
            # The whole point of a real propensity: it must not be the
            # deterministic policies' flat 1.0.
            assert 0.0 < row.propensity < 1.0

    async def test_flag_off_returns_an_empty_deck_and_logs_nothing(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        session.add(
            FeatureFlag(key="exploration_deck", enabled=False, description="off for this test")
        )
        await session.commit()

        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000014", slug="topic-off")
        article = await make_article(session, source)
        await _tag(session, article_id=article.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)

        assert response.status_code == 200
        assert response.json()["cards"] == []
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows == []

    async def test_excluded_articles_never_appear(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:20000015", slug="topic-excluded")
        kept = await make_article(session, source, title="Kept")
        excluded = await make_article(session, source, title="Excluded")
        await _tag(session, article_id=kept.id, topic_id=topic.id)
        await _tag(session, article_id=excluded.id, topic_id=topic.id)
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/not-interested",
            json={"article_id": excluded.id, "surface": "onboarding"},
            headers=headers,
        )

        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)
        titles = [card["article"]["title"] for card in response.json()["cards"]]
        assert "Excluded" not in titles
        assert "Kept" in titles

    async def test_a_reader_without_beta_access_is_forbidden(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session, redeem_invite=False)
        response = await client.get("/v1/exploration-deck?locale=en", headers=headers)
        assert response.status_code == 403
