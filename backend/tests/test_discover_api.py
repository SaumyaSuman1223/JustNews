"""GET /v1/discover and ranker v2 behind /v1/feed (ADR 0015), against a real
database. Tests use the hashing embedder, where headlines sharing words are
near each other - enough to see a profile pull its own kind of story up."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.feed import CHRONOLOGICAL_POLICY, HEURISTIC_V2_POLICY
from justnews_core.db import set_current_user
from justnews_core.models import ArticleTopic, Impression, UserProfile, UserSourceFollow

CONSENTED = {"x-analytics-consent": "granted", "x-session-id": "anon-1"}


async def _corpus(session: AsyncSession, *, sources: int = 6, per_source: int = 5) -> None:
    for s in range(sources):
        source = await make_source(session, slug=f"outlet-{s}")
        for a in range(per_source):
            await make_article(
                session, source, title=f"Report {a} from outlet {s}", minutes_ago=s * 7 + a * 11
            )
    await session.commit()


async def _signed_in(session: AsyncSession) -> tuple[uuid.UUID, dict[str, str]]:
    """A signed-in reader without an invite: ranked by v2 directly."""
    user_id = uuid.uuid4()
    session.add(UserProfile(id=user_id))
    await session.commit()
    return user_id, {"authorization": f"Bearer {make_access_token(user_id=str(user_id))}"}


class TestTop:
    async def test_signed_out_top_is_ranked_and_logs_nothing(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _corpus(session)
        body = (await client.get("/v1/discover", params={"view": "top"})).json()
        assert len(body["items"]) == 20
        assert [item["position"] for item in body["items"]] == list(range(20))
        assert all(item["impression_id"] is None for item in body["items"])
        assert (await session.execute(select(Impression))).first() is None

    async def test_reaches_back_by_time_not_by_count(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Yesterday's", minutes_ago=60 * 30)
        await make_article(session, source, title="Last week's", minutes_ago=60 * 24 * 6)
        await session.commit()
        titles = [
            item["article"]["title"]
            for item in (await client.get("/v1/discover", params={"view": "top"})).json()["items"]
        ]
        assert titles == ["Yesterday's"]

    async def test_consented_pages_log_real_probabilities_without_repeats(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _corpus(session)
        seen: list[int] = []
        cursor = None
        for _ in range(3):
            params: dict[str, object] = {"view": "top", "page_size": 10}
            if cursor:
                params["cursor"] = cursor
            body = (await client.get("/v1/discover", params=params, headers=CONSENTED)).json()
            seen += [item["article"]["id"] for item in body["items"]]
            cursor = body["next_cursor"]
            assert all(item["impression_id"] is not None for item in body["items"])
        assert len(seen) == len(set(seen)) == 30

        rows = (await session.execute(select(Impression))).scalars().all()
        assert sorted(row.position for row in rows) == list(range(30))
        assert {row.surface for row in rows} == {"top"}
        assert {row.ranking_policy for row in rows} == {HEURISTIC_V2_POLICY}
        assert all(0 < row.propensity <= 1 for row in rows)
        assert any(row.propensity < 1 for row in rows)

    async def test_no_publisher_fills_the_page(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        busy = await make_source(session, slug="busy")
        for index in range(30):
            await make_article(session, busy, title=f"Brief {index}", minutes_ago=index)
        for s in range(4):
            quiet = await make_source(session, slug=f"quiet-{s}")
            await make_article(session, quiet, title=f"Feature {s}", minutes_ago=120)
        await session.commit()

        body = (await client.get("/v1/discover", params={"view": "top", "page_size": 9})).json()
        slugs = [item["article"]["source_slug"] for item in body["items"]]
        assert slugs.count("busy") <= 5
        assert {"quiet-0", "quiet-1", "quiet-2", "quiet-3"} <= set(slugs)


class TestForYou:
    async def test_device_history_pulls_its_kind_of_story_up(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        read = [
            await make_article(
                session, source, title="Cricket test match India wins", minutes_ago=90
            ),
            await make_article(
                session, source, title="Cricket test series India squad", minutes_ago=95
            ),
        ]
        other = await make_source(session, slug="other")
        for index in range(6):
            await make_article(
                session, other, title=f"Parliament budget vote {index}", minutes_ago=5
            )
        await make_article(session, source, title="Cricket test match India draw", minutes_ago=60)
        await session.commit()

        body = (
            await client.get(
                "/v1/discover",
                params={"view": "for_you", "history": ",".join(str(a.id) for a in read)},
            )
        ).json()
        assert body["items"][0]["article"]["title"] == "Cricket test match India draw"
        assert body["items"][0]["reason"] == {"kind": "similar", "topic_id": None}

    async def test_a_followed_source_leads(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        user_id, headers = await _signed_in(session)
        favourite = await make_source(session, slug="favourite")
        await make_article(session, favourite, title="From the favourite", minutes_ago=240)
        other = await make_source(session, slug="other")
        await make_article(session, other, title="Newer elsewhere", minutes_ago=200)
        session.add(UserSourceFollow(user_id=user_id, source_id=favourite.id))
        await session.commit()

        body = (
            await client.get("/v1/discover", params={"view": "for_you"}, headers=headers)
        ).json()
        assert body["items"][0]["article"]["title"] == "From the favourite"
        assert body["items"][0]["reason"]["kind"] == "followed_source"

    async def test_shown_and_passed_over_sinks(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        user_id, headers = await _signed_in(session)
        one = await make_source(session, slug="one")
        two = await make_source(session, slug="two")
        stale = await make_article(session, one, title="Shown twice", minutes_ago=30)
        await make_article(session, two, title="Never shown", minutes_ago=31)
        for hours in (5, 3):
            session.add(
                Impression(
                    user_id=user_id,
                    session_id="earlier",
                    article_id=stale.id,
                    position=0,
                    surface="feed",
                    locale="en",
                    propensity=1.0,
                    ranking_policy=HEURISTIC_V2_POLICY,
                    served_at=datetime.now(UTC) - timedelta(hours=hours),
                )
            )
        await session.commit()

        body = (
            await client.get("/v1/discover", params={"view": "for_you"}, headers=headers)
        ).json()
        assert [item["article"]["title"] for item in body["items"]] == [
            "Never shown",
            "Shown twice",
        ]

    async def test_invited_readers_go_through_the_experiment(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _corpus(session, sources=2, per_source=2)
        for policy in (CHRONOLOGICAL_POLICY, HEURISTIC_V2_POLICY):
            user_id = find_user_id_for_policy(policy)
            headers = await make_beta_headers(session, user_id=user_id)
            await client.get(
                "/v1/discover", params={"view": "for_you"}, headers={**headers, **CONSENTED}
            )
            await set_current_user(session, user_id)
            rows = (
                (await session.execute(select(Impression).where(Impression.user_id == user_id)))
                .scalars()
                .all()
            )
            assert rows and {row.ranking_policy for row in rows} == {policy}


class TestTopic:
    async def test_only_the_topics_articles(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        topic = await make_topic(session)
        source = await make_source(session)
        tagged = await make_article(session, source, title="In the topic", minutes_ago=60 * 50)
        await make_article(session, source, title="Elsewhere", minutes_ago=5)
        session.add(ArticleTopic(article_id=tagged.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        body = (
            await client.get("/v1/discover", params={"view": "topic", "topic": topic.id})
        ).json()
        assert [item["article"]["title"] for item in body["items"]] == ["In the topic"]

    async def test_needs_a_topic(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/discover", params={"view": "topic"})).status_code == 422


class TestValidation:
    async def test_history_must_be_ids(self, client: AsyncClient) -> None:
        response = await client.get("/v1/discover", params={"view": "for_you", "history": "1,x"})
        assert response.status_code == 422

    async def test_a_cursor_from_another_ranker_is_refused(self, client: AsyncClient) -> None:
        response = await client.get("/v1/discover", params={"view": "top", "cursor": "e30"})
        assert response.status_code == 422


class TestFeedV2:
    async def test_pages_join_without_repeats_and_log_positions(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _corpus(session)
        user_id = find_user_id_for_policy(HEURISTIC_V2_POLICY)
        headers = {**(await make_beta_headers(session, user_id=user_id)), **CONSENTED}
        ids: list[int] = []
        cursor = None
        for _ in range(2):
            params: dict[str, object] = {"page_size": 12}
            if cursor:
                params["cursor"] = cursor
            body = (await client.get("/v1/feed", params=params, headers=headers)).json()
            ids += [item["article"]["id"] for item in body["items"]]
            assert [item["position"] for item in body["items"]] == list(
                range(len(ids) - len(body["items"]), len(ids))
            )
            cursor = body["next_cursor"]
        assert len(ids) == len(set(ids)) == 24

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert sorted(row.position for row in rows) == list(range(24))
        assert {row.ranking_policy for row in rows} == {HEURISTIC_V2_POLICY}
