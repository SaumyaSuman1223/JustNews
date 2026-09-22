"""Integration tests for the read-side content routes."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, StoryCluster


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


class TestArticleCoverage:
    """Third-pass audit §21's diversity line, exposed as `coverage` on
    `ArticleOut` - real `story_clusters` counts, never inferred."""

    async def test_an_article_outside_any_cluster_has_no_coverage(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="A standalone story")
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["story_cluster_id"] is None
        assert body["coverage"] is None

    async def test_exposes_the_source_role_when_assigned(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session, source_role="industry")
        article = await make_article(session, source, title="An industry press story")
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["source_role"] == "industry"

    async def test_source_role_is_null_when_unassigned(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="An unroled story")
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["source_role"] is None

    async def test_an_article_in_a_cluster_reports_real_counts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        uk = await make_source(session, slug="uk-wire", country="GB")
        us = await make_source(session, slug="us-wire", country="US")
        first_seen = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
        last_seen = datetime(2026, 9, 3, 18, 0, tzinfo=UTC)
        cluster = StoryCluster(
            title="A widely covered story",
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            article_count=2,
            source_count=2,
            language_count=1,
            country_count=2,
        )
        session.add(cluster)
        await session.flush()
        article = await make_article(session, uk, title="From the UK wire")
        article.story_cluster_id = cluster.id
        other = await make_article(session, us, title="From the US wire")
        other.story_cluster_id = cluster.id
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["story_cluster_id"] == cluster.id
        assert body["coverage"] == {
            "articles": 2,
            "sources": 2,
            "languages": 1,
            "countries": 2,
            "first_seen_at": "2026-09-01T06:00:00Z",
            "last_seen_at": "2026-09-03T18:00:00Z",
        }

    async def test_a_single_source_cluster_reports_one_honestly(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # A cluster of one source is still a real cluster - this is the case
        # the frontend uses to decide *not* to show a diversity line, and it
        # has to be able to tell "not clustered" (coverage: null) apart from
        # "clustered, but only one source so far" (coverage.sources == 1).
        source = await make_source(session)
        cluster = StoryCluster(
            title="A story with one source so far",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            article_count=1,
            source_count=1,
            language_count=1,
            country_count=1,
        )
        session.add(cluster)
        await session.flush()
        article = await make_article(session, source, title="The only report")
        article.story_cluster_id = cluster.id
        await session.commit()

        body = (await client.get(f"/v1/articles/{article.id}")).json()
        assert body["coverage"]["sources"] == 1

    async def test_the_feed_carries_coverage_too_not_only_the_single_article_route(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        uk = await make_source(session, slug="uk-wire-2", country="GB")
        us = await make_source(session, slug="us-wire-2", country="US")
        cluster = StoryCluster(
            title="A story on the feed",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            article_count=2,
            source_count=2,
            language_count=1,
            country_count=2,
        )
        session.add(cluster)
        await session.flush()
        article = await make_article(session, uk, title="Feed story A")
        article.story_cluster_id = cluster.id
        other = await make_article(session, us, title="Feed story B")
        other.story_cluster_id = cluster.id
        await session.commit()

        items = (await client.get("/v1/articles")).json()["items"]
        by_id = {item["id"]: item for item in items}
        assert by_id[article.id]["coverage"]["sources"] == 2
        assert by_id[other.id]["coverage"]["sources"] == 2


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

    async def test_category_is_the_articles_shared_primary_topic(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session, topic_id="medtop:60000001", slug="story-category")
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="Categorised story",
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
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        response = await client.get(f"/v1/stories/{cluster.id}")
        body = response.json()
        assert body["category"]["id"] == topic.id

    async def test_no_shared_primary_topic_is_no_category(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="Uncategorised story",
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
        await session.commit()

        response = await client.get(f"/v1/stories/{cluster.id}")
        assert response.json()["category"] is None

    async def test_perspectives_group_the_clusters_own_articles(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        industry = await make_source(session, slug="story-persp-industry", source_role="industry")
        wire = await make_source(session, slug="story-persp-wire", source_role="wire")
        now = datetime.now(UTC)
        cluster = StoryCluster(
            title="Story with perspectives",
            first_seen_at=now,
            last_seen_at=now,
            article_count=2,
            source_count=2,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()
        for source in (industry, wire):
            article = await make_article(session, source, title=f"From {source.slug}")
            article.story_cluster_id = cluster.id
        await session.commit()

        response = await client.get(f"/v1/stories/{cluster.id}")
        body = response.json()
        assert [g["role"] for g in body["perspectives"]] == ["industry"]
        assert body["perspectives"][0]["sources"][0]["slug"] == "story-persp-industry"


class TestSources:
    async def test_filters_to_the_requested_language(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await make_source(session, slug="hindi-source", language="hi", name="Hindi Source")
        await make_source(session, slug="english-source", language="en", name="English Source")
        await session.commit()

        body = (await client.get("/v1/sources", params={"language": "hi"})).json()
        assert [row["name"] for row in body] == ["Hindi Source"]

    async def test_an_inactive_source_is_excluded(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await make_source(session, slug="retired", language="en", active=False)
        await session.commit()

        body = (await client.get("/v1/sources", params={"language": "en"})).json()
        assert body == []

    async def test_higher_trust_sources_come_first(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await make_source(session, slug="low-trust", language="en", trust_score=0.3, name="Low")
        await make_source(session, slug="high-trust", language="en", trust_score=0.9, name="High")
        await session.commit()

        body = (await client.get("/v1/sources", params={"language": "en"})).json()
        assert [row["name"] for row in body] == ["High", "Low"]

    async def test_rejects_an_invalid_language_code(self, client: AsyncClient) -> None:
        response = await client.get("/v1/sources", params={"language": "zzzz9"})
        assert response.status_code == 422

    async def test_omitting_language_returns_the_complete_catalogue(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Search's source filter (audit §27) needs every source, not one
        language's bounded discovery sample - omitting `language` is how it
        asks for that, alphabetical rather than trust-ranked."""
        await make_source(session, slug="hindi-source", language="hi", name="Hindi Source")
        await make_source(session, slug="english-source", language="en", name="English Source")
        await session.commit()

        body = (await client.get("/v1/sources")).json()
        assert [row["name"] for row in body] == ["English Source", "Hindi Source"]

    async def test_omitting_language_still_excludes_inactive_sources(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await make_source(session, slug="retired", active=False)
        await session.commit()

        body = (await client.get("/v1/sources")).json()
        assert body == []


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


class TestTopArticles:
    """Signed-out Home's "What matters" (fifth pass §2.3): importance by
    recency x breadth of coverage x source trust, not newest-first."""

    async def _cluster(self, session: AsyncSession, articles: list, sources: int) -> StoryCluster:
        cluster = StoryCluster(
            title=articles[0].title,
            first_seen_at=articles[0].published_at,
            last_seen_at=articles[-1].published_at,
            article_count=len(articles),
            source_count=sources,
            language_count=1,
            country_count=1,
        )
        session.add(cluster)
        await session.flush()
        for article in articles:
            article.story_cluster_id = cluster.id
        return cluster

    async def test_a_widely_carried_story_outranks_a_newer_single_outlet_one(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        wires = [await make_source(session, slug=f"wire-{i}") for i in range(4)]
        broad = [
            await make_article(
                session, wire, title=f"Summit agrees climate fund {i}", minutes_ago=90
            )
            for i, wire in enumerate(wires)
        ]
        await self._cluster(session, broad, sources=4)
        lone = await make_article(
            session, wires[0], title="Celebrity feud escalates", minutes_ago=5
        )
        await session.commit()

        body = (await client.get("/v1/articles/top?languages=en&limit=5")).json()
        ids = [item["id"] for item in body]
        # The broad story leads, represented once, and the newer lone piece
        # still makes the list - just below it.
        assert ids[0] in {article.id for article in broad}
        assert lone.id in ids[1:]

    async def test_one_article_per_story(self, client: AsyncClient, session: AsyncSession) -> None:
        wires = [await make_source(session, slug=f"desk-{i}") for i in range(3)]
        members = [
            await make_article(session, wire, title=f"Election result {i}")
            for i, wire in enumerate(wires)
        ]
        cluster = await self._cluster(session, members, sources=3)
        await session.commit()

        body = (await client.get("/v1/articles/top?languages=en&limit=10")).json()
        assert sum(1 for item in body if item["story_cluster_id"] == cluster.id) == 1

    async def test_top_is_not_read_as_an_article_id(self, client: AsyncClient) -> None:
        response = await client.get("/v1/articles/top")
        assert response.status_code == 200
        assert response.json() == []
