"""Stage 9's engagement surfaces: trending, followed sources, editions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article, InteractionEvent


async def _click(
    session: AsyncSession, article: Article, *, times: int, hours_ago: float = 0.0
) -> None:
    when = datetime.now(UTC) - timedelta(hours=hours_ago)
    for index in range(times):
        session.add(
            InteractionEvent(
                user_id=None,
                session_id=f"session-{article.id}-{index}",
                article_id=article.id,
                event_type="click",
                surface="feed",
                locale="en",
                position=0,
                created_at=when,
            )
        )
    await session.flush()


class TestTrending:
    async def test_ranks_by_clicks_not_recency(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # The whole reason this rail earns its place beside a recency-ordered
        # feed: it must be able to disagree with the feed.
        source = await make_source(session)
        newest = await make_article(session, source, title="Newest but ignored", minutes_ago=1)
        older = await make_article(session, source, title="Older but clicked", minutes_ago=300)
        await _click(session, older, times=5)
        await _click(session, newest, times=1)
        await session.commit()

        titles = [row["title"] for row in (await client.get("/v1/trending")).json()]
        assert titles[0] == "Older but clicked"

    async def test_an_unclicked_article_is_not_trending(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Nobody clicked this")
        clicked = await make_article(session, source, title="Clicked once")
        await _click(session, clicked, times=1)
        await session.commit()

        titles = [row["title"] for row in (await client.get("/v1/trending")).json()]
        assert titles == ["Clicked once"]

    async def test_clicks_outside_the_window_do_not_count(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        stale = await make_article(session, source, title="Popular last week")
        await _click(session, stale, times=20, hours_ago=72)
        await session.commit()

        assert (await client.get("/v1/trending")).json() == []

    async def test_respects_the_language_filter(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        english = await make_article(session, source, title="English", language="en")
        spanish = await make_article(session, source, title="Español", language="es")
        await _click(session, english, times=3)
        await _click(session, spanish, times=3)
        await session.commit()

        rows = (await client.get("/v1/trending", params={"languages": "es"})).json()
        assert [row["title"] for row in rows] == ["Español"]


class TestFollowedSources:
    async def test_follow_then_list_then_unfollow(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session, slug="the-guardian")
        await session.commit()
        headers = await make_beta_headers(session)

        created = await client.post(
            "/v1/follows/sources", headers=headers, json={"source_id": source.id}
        )
        assert created.status_code == 201
        assert created.json()["slug"] == "the-guardian"

        listed = (await client.get("/v1/follows/sources", headers=headers)).json()
        assert [row["source_id"] for row in listed] == [source.id]

        removed = await client.delete(f"/v1/follows/sources/{source.id}", headers=headers)
        assert removed.status_code == 204
        assert (await client.get("/v1/follows/sources", headers=headers)).json() == []

    async def test_following_twice_is_idempotent(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Pressing follow twice is one preference, not an error.
        source = await make_source(session)
        await session.commit()
        headers = await make_beta_headers(session)

        for _ in range(2):
            response = await client.post(
                "/v1/follows/sources", headers=headers, json={"source_id": source.id}
            )
            assert response.status_code == 201

        assert len((await client.get("/v1/follows/sources", headers=headers)).json()) == 1

    async def test_following_an_unknown_source_is_a_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/follows/sources", headers=headers, json={"source_id": 999_999}
        )
        assert response.status_code == 404

    async def test_source_follows_are_separate_from_topic_follows(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await session.commit()
        headers = await make_beta_headers(session)

        await client.post("/v1/follows/sources", headers=headers, json={"source_id": source.id})

        # The topic endpoint must not have grown a source in it.
        assert (await client.get("/v1/follows", headers=headers)).json() == []

    async def test_requires_sign_in(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/follows/sources")).status_code == 401


class TestEditions:
    async def test_lists_editions_default_first(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from justnews_ingestion.seed import seed_editions

        await seed_editions(session)
        await session.commit()

        rows = (await client.get("/v1/editions")).json()
        assert rows, "seeded editions should be listed"
        assert rows[0]["is_default"] is True

    async def test_filters_editions_by_language(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from justnews_ingestion.seed import seed_editions

        await seed_editions(session)
        await session.commit()

        rows = (await client.get("/v1/editions", params={"languages": "hi"})).json()
        assert rows and all(row["language"] == "hi" for row in rows)
