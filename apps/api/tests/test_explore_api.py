"""/v1/explore - latest news, ranked, for everyone.

The properties that matter: it works without an account (that is who it is
for), it is ranked rather than a raw newest-first dump, it never returns the
same story twice, and it logs its own surface and policy so its CTR can be
compared against the personalised feed's.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.explore import EXPLORE_POLICY
from justnews_core.db import set_current_user
from justnews_core.models import Impression, StoryCluster


class TestAnonymousAccess:
    async def test_works_with_no_credentials_at_all(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Anyone can read this")
        await session.commit()

        response = await client.get("/v1/explore")

        assert response.status_code == 200
        titles = [item["article"]["title"] for item in response.json()["items"]]
        assert "Anyone can read this" in titles

    async def test_an_anonymous_read_still_logs_impressions(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Logged for a stranger")
        await session.commit()

        response = await client.get("/v1/explore", headers={"x-session-id": "browsing-session-abc"})
        assert response.status_code == 200

        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows, "explore must log impressions even with no account"
        assert all(row.user_id is None for row in rows)
        assert all(row.session_id == "browsing-session-abc" for row in rows)

    async def test_items_carry_their_impression_id(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Without this a click from explore cannot be attributed to what
        # served it, which is the whole reason impressions exist.
        source = await make_source(session)
        await make_article(session, source, title="Attributable")
        await session.commit()

        items = (await client.get("/v1/explore")).json()["items"]
        assert items and all(isinstance(item["impression_id"], int) for item in items)


class TestSurfaceAndPolicy:
    async def test_logs_the_explore_surface_and_its_own_policy(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Surfaced")
        await session.commit()

        assert (await client.get("/v1/explore")).status_code == 200

        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows
        assert all(row.surface == "explore" for row in rows)
        # Recorded alongside the feed's policies rather than in a separate
        # column, so explore CTR is comparable with them.
        assert all(row.ranking_policy == EXPLORE_POLICY for row in rows)


class TestRanking:
    async def test_returns_one_article_per_story_cluster(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        cluster = StoryCluster(
            title="One event, many write-ups",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            article_count=3,
            source_count=3,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()
        for title in ("Wire copy A", "Wire copy B", "Wire copy C"):
            article = await make_article(session, source, title=title)
            article.story_cluster_id = cluster.id
        await session.commit()

        titles = [
            item["article"]["title"] for item in (await client.get("/v1/explore")).json()["items"]
        ]
        from_cluster = [t for t in titles if t.startswith("Wire copy")]
        assert len(from_cluster) == 1, f"expected one per cluster, got {from_cluster}"

    async def test_paginates_without_repeating_an_article(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        for index in range(9):
            await make_article(session, source, title=f"Story {index:02d}", minutes_ago=index)
        await session.commit()

        seen: list[int] = []
        cursor: str | None = None
        for _ in range(5):
            params = {"page_size": 3} | ({"cursor": cursor} if cursor else {})
            page = (await client.get("/v1/explore", params=params)).json()
            seen.extend(item["article"]["id"] for item in page["items"])
            cursor = page["next_cursor"]
            if not cursor:
                break

        assert len(seen) == len(set(seen)), "an article was served twice across pages"
        assert len(seen) == 9

    async def test_filters_to_the_requested_languages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Inglés", language="en")
        await make_article(session, source, title="Español", language="es")
        await session.commit()

        items = (await client.get("/v1/explore", params={"languages": "es"})).json()["items"]
        assert items and all(item["article"]["language"] == "es" for item in items)


class TestSignedIn:
    async def test_a_signed_in_reader_has_their_impressions_attributed(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Explore needs no beta invite - it is the surface a reader sees
        # before they have one - but a signed-in read is still theirs.
        source = await make_source(session)
        await make_article(session, source, title="Mine")
        await session.commit()

        user_id = str(uuid.uuid4())
        headers = {"authorization": f"Bearer {make_access_token(user_id)}"}
        assert (await client.get("/v1/explore", headers=headers)).status_code == 200

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(str(row.user_id) == user_id for row in rows)

    async def test_excludes_articles_the_reader_marked_not_interested(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        rejected = await make_article(session, source, title="Not for me")
        await make_article(session, source, title="Fine")
        await session.commit()

        # /v1/not-interested is behind the beta gate, so recording the signal
        # needs an invited reader - explore itself still does not.
        headers = await make_beta_headers(session)
        marked = await client.post(
            "/v1/not-interested",
            headers=headers,
            json={"article_id": rejected.id, "surface": "explore"},
        )
        assert marked.status_code == 204, marked.text

        titles = [
            item["article"]["title"]
            for item in (await client.get("/v1/explore", headers=headers)).json()["items"]
        ]
        assert "Not for me" not in titles
        assert "Fine" in titles
