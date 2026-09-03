"""Integration tests for authentication and the /me profile route."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, Topic


class TestAuthentication:
    async def test_missing_token_is_401_in_the_standard_envelope(self, client: AsyncClient) -> None:
        response = await client.get("/v1/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"

    async def test_garbage_token_is_401(self, client: AsyncClient) -> None:
        response = await client.get("/v1/me", headers={"authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    async def test_wrong_audience_is_401(self, client: AsyncClient) -> None:
        token = make_access_token(audience="some-other-app")
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 401

    async def test_expired_token_is_401(self, client: AsyncClient) -> None:
        token = make_access_token(expires_in=-60)
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 401


class TestMe:
    async def test_first_request_creates_the_profile(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["preferred_languages"] == []

    async def test_updates_preferred_languages(self, client: AsyncClient) -> None:
        token = make_access_token()
        headers = {"authorization": f"Bearer {token}"}
        response = await client.patch(
            "/v1/me", json={"preferred_languages": ["en", "es", "en"]}, headers=headers
        )
        assert response.status_code == 200
        # Deduplicated, order preserved.
        assert response.json()["preferred_languages"] == ["en", "es"]

        # And it sticks.
        again = await client.get("/v1/me", headers=headers)
        assert again.json()["preferred_languages"] == ["en", "es"]

    async def test_rejects_an_invalid_language(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.patch(
            "/v1/me",
            json={"preferred_languages": ["zzzz9"]},
            headers={"authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_each_user_sees_only_their_own_profile(self, client: AsyncClient) -> None:
        alice = make_access_token()
        bob = make_access_token()
        await client.patch(
            "/v1/me",
            json={"preferred_languages": ["ar"]},
            headers={"authorization": f"Bearer {alice}"},
        )

        bob_profile = await client.get("/v1/me", headers={"authorization": f"Bearer {bob}"})
        assert bob_profile.json()["preferred_languages"] == []


class TestReadingProfile:
    async def test_empty_with_no_history(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session)
        response = await client.get("/v1/me/reading-profile", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"sampled": 0, "languages": [], "topics": []}

    async def test_breaks_down_by_language_and_by_primary_topic(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        en_article = await make_article(session, source, title="English one", language="en")
        es_article = await make_article(session, source, title="Spanish one", language="es")
        topic = await make_topic(session, topic_id="medtop:20000344", slug="conflict")
        session.add(ArticleTopic(article_id=en_article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        for article in (en_article, en_article, es_article):
            report = await client.post(
                "/v1/history",
                json={"article_id": article.id, "surface": "feed"},
                headers=headers,
            )
            assert report.status_code == 204

        response = await client.get("/v1/me/reading-profile", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["sampled"] == 3
        assert {row["language"]: row["count"] for row in body["languages"]} == {"en": 2, "es": 1}
        # Falls back to a humanised slug: no TopicLabel row was seeded for it.
        assert body["topics"] == [{"topic_id": topic.id, "label": "Conflict", "count": 1}]

    async def test_a_nested_topic_rolls_up_to_its_top_level_ancestor(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        top_level = await make_topic(session, topic_id="medtop:20000105", slug="disaster")
        nested = Topic(
            id="medtop:20000106",
            parent_id=top_level.id,
            level=2,
            path=[top_level.id, "medtop:20000106"],
            slug="earthquake",
        )
        session.add(nested)
        await session.flush()
        session.add(ArticleTopic(article_id=article.id, topic_id=nested.id, is_primary=True))
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/history", json={"article_id": article.id, "surface": "feed"}, headers=headers
        )

        body = (await client.get("/v1/me/reading-profile", headers=headers)).json()
        # Counted under the level-1 ancestor, not the leaf the article was
        # actually tagged with - the picker (and this breakdown) only ever
        # shows the ~17 top-level concepts.
        assert body["topics"] == [{"topic_id": top_level.id, "label": "Disaster", "count": 1}]

    async def test_a_reader_never_sees_another_readers_reading_profile(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        alice = await make_beta_headers(session)
        bob = await make_beta_headers(session)
        await client.post(
            "/v1/history", json={"article_id": article.id, "surface": "feed"}, headers=alice
        )

        bob_profile = await client.get("/v1/me/reading-profile", headers=bob)
        assert bob_profile.json() == {"sampled": 0, "languages": [], "topics": []}
