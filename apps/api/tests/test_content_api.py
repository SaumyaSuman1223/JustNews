"""Integration tests for the read-side content routes."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import StoryCluster


class TestHealth:
    async def test_liveness_never_touches_the_database(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_every_response_carries_a_request_id(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.headers["x-request-id"]

    async def test_a_supplied_request_id_is_echoed_back(self, client: AsyncClient) -> None:
        # Lets a trace survive across the web tier and the API.
        response = await client.get("/health", headers={"x-request-id": "abc123"})
        assert response.headers["x-request-id"] == "abc123"


class TestListArticles:
    async def test_empty_corpus_returns_an_empty_page(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/articles")).json()
        assert body == {"items": [], "next_cursor": None}

    async def test_returns_newest_first(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Oldest", minutes_ago=300)
        await make_article(session, source, title="Newest", minutes_ago=1)
        await make_article(session, source, title="Middle", minutes_ago=60)
        await session.commit()

        titles = [item["title"] for item in (await client.get("/v1/articles")).json()["items"]]
        assert titles == ["Newest", "Middle", "Oldest"]

    async def test_language_filter_excludes_everything_else(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # No reader receives a language they did not ask for.
        source = await make_source(session)
        await make_article(session, source, title="English", language="en")
        await make_article(session, source, title="Español", language="es")
        await make_article(session, source, title="عربي", language="ar")
        await session.commit()

        body = (await client.get("/v1/articles?languages=es,ar")).json()
        assert {item["language"] for item in body["items"]} == {"es", "ar"}

    async def test_rejects_an_invalid_language_code(self, client: AsyncClient) -> None:
        response = await client.get("/v1/articles?languages=zzzz9")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_topic_filter_excludes_untagged_articles(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from justnews_core.models import ArticleTopic, Topic

        source = await make_source(session)
        tagged = await make_article(session, source, title="Tagged")
        await make_article(session, source, title="Untagged")
        session.add(Topic(id="medtop:99000002", level=1, path=["medtop:99000002"], slug="t"))
        await session.flush()
        session.add(ArticleTopic(article_id=tagged.id, topic_id="medtop:99000002"))
        await session.commit()

        body = (await client.get("/v1/articles?topic=medtop:99000002")).json()
        assert [item["title"] for item in body["items"]] == ["Tagged"]

    async def test_pagination_visits_every_article_exactly_once(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # The property offset pagination cannot guarantee on a live feed.
        source = await make_source(session)
        for index in range(25):
            await make_article(session, source, title=f"Article {index}", minutes_ago=index)
        await session.commit()

        seen: list[int] = []
        cursor: str | None = None
        for _ in range(10):
            url = f"/v1/articles?page_size=7{f'&cursor={cursor}' if cursor else ''}"
            body = (await client.get(url)).json()
            seen.extend(item["id"] for item in body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                break

        assert len(seen) == 25
        assert len(set(seen)) == 25

    async def test_last_page_has_no_cursor(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Only one")
        await session.commit()
        assert (await client.get("/v1/articles")).json()["next_cursor"] is None

    async def test_articles_sharing_a_timestamp_do_not_repeat(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Feeds publish in batches, so identical timestamps are normal. The
        # cursor breaks the tie on id; without that these would loop forever.
        from datetime import UTC, datetime

        source = await make_source(session)
        when = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
        for index in range(6):
            await make_article(session, source, title=f"Batch {index}", published_at=when)
        await session.commit()

        seen: list[int] = []
        cursor: str | None = None
        for _ in range(6):
            url = f"/v1/articles?page_size=2{f'&cursor={cursor}' if cursor else ''}"
            body = (await client.get(url)).json()
            seen.extend(item["id"] for item in body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                break

        assert sorted(seen) == sorted(set(seen))
        assert len(seen) == 6

    async def test_rejects_an_oversized_page(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/articles?page_size=500")).status_code == 422

    async def test_rejects_a_malformed_cursor(self, client: AsyncClient) -> None:
        response = await client.get("/v1/articles?cursor=garbage")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestGetArticle:
    async def test_returns_the_publisher_url_to_link_out_to(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(
            session, source, title="Story", url="https://pub.example/story"
        )
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["url"] == "https://pub.example/story"
        assert body["source_name"] == source.name

    async def test_never_exposes_article_body_text(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # There is no body column, and this test exists so that adding one
        # breaks something loudly.
        source = await make_source(session)
        article = await make_article(session, source, snippet="A short summary.")
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert set(body) & {"body", "content", "full_text", "text"} == set()

    async def test_unknown_id_is_a_404_in_the_standard_envelope(self, client: AsyncClient) -> None:
        response = await client.get("/v1/articles/99999999")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "not_found"
        assert error["request_id"]


class TestGetStory:
    async def test_returns_every_member_article_cross_lingual(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="A shared event",
            first_seen_at=now,
            last_seen_at=now,
            article_count=2,
            source_count=1,
            language_count=2,
        )
        session.add(cluster)
        await session.flush()
        en = await make_article(session, source, title="English take", language="en")
        es = await make_article(session, source, title="Toma en español", language="es")
        en.story_cluster_id = cluster.id
        es.story_cluster_id = cluster.id
        await session.commit()

        response = await client.get(f"/v1/stories/{cluster.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["story"]["id"] == cluster.id
        assert {a["language"] for a in body["articles"]} == {"en", "es"}

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/stories/99999999")
        assert response.status_code == 404


class TestStats:
    async def test_counts_distinct_languages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        for language in ("en", "es", "ar", "en"):
            await make_article(session, source, title=f"t{language}", language=language)
        await session.commit()

        body = (await client.get("/v1/stats")).json()
        assert body["articles"] == 4
        assert body["languages"] == 3


class TestDatabaseOutage:
    """A database outage must degrade, not look like a bug in the request."""

    async def test_reads_return_503_with_retry_after(
        self, client: AsyncClient, monkeypatch: object
    ) -> None:
        from justnews_api.routers import content

        async def refuse() -> None:
            raise ConnectionRefusedError(111, "Connection refused")

        client._transport.app.dependency_overrides[content.get_session] = refuse  # type: ignore[attr-defined]
        try:
            response = await client.get("/v1/articles")
        finally:
            client._transport.app.dependency_overrides.pop(content.get_session, None)  # type: ignore[attr-defined]

        # 503 + Retry-After tells a cache it may keep serving what it has.
        # A 500 would say "this request was wrong" and invite a retry storm.
        assert response.status_code == 503
        assert response.headers["retry-after"] == "15"
        assert response.json()["error"]["code"] == "database_unavailable"

    async def test_liveness_still_passes(self, client: AsyncClient) -> None:
        # /health must never touch the database, or an outage makes the
        # orchestrator kill healthy containers.
        assert (await client.get("/health")).status_code == 200
