"""Integration tests for the personalised feed and impression logging."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import set_current_user
from justnews_core.models import Impression


class TestFeed:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/feed")).status_code == 401

    async def test_newest_first(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Oldest", minutes_ago=60)
        await make_article(session, source, title="Newest", minutes_ago=1)
        await session.commit()

        headers = await make_beta_headers(session)
        body = (await client.get("/v1/feed", headers=headers)).json()
        assert [item["title"] for item in body["items"]] == ["Newest", "Oldest"]

    async def test_every_served_item_logs_an_impression_with_propensity(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await make_article(session, source, title="B")
        await session.commit()

        user_id = str(uuid.uuid4())
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-session-id"] = "sess-1"
        await client.get("/v1/feed", headers=headers)

        # RLS on impressions is FORCE-enabled - even this test session must
        # identify as the reader whose rows it wants to see.
        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert len(rows) == 2
        assert {row.position for row in rows} == {0, 1}
        assert all(row.propensity == 1.0 for row in rows)
        assert all(row.surface == "feed" for row in rows)
        assert all(row.session_id == "sess-1" for row in rows)

    async def test_not_interested_articles_are_excluded(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Keep")
        hide = await make_article(session, source, title="Hide")
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/not-interested",
            json={"article_id": hide.id, "surface": "feed"},
            headers=headers,
        )

        body = (await client.get("/v1/feed", headers=headers)).json()
        titles = [item["title"] for item in body["items"]]
        assert titles == ["Keep"]

    async def test_falls_back_to_profile_languages_when_unspecified(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="English", language="en")
        await make_article(session, source, title="Español", language="es")
        await session.commit()

        headers = await make_beta_headers(session)
        await client.patch("/v1/me", json={"preferred_languages": ["es"]}, headers=headers)

        body = (await client.get("/v1/feed", headers=headers)).json()
        assert [item["language"] for item in body["items"]] == ["es"]

    async def test_explicit_languages_override_the_profile(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="English", language="en")
        await make_article(session, source, title="Español", language="es")
        await session.commit()

        headers = await make_beta_headers(session)
        await client.patch("/v1/me", json={"preferred_languages": ["es"]}, headers=headers)

        body = (await client.get("/v1/feed?languages=en", headers=headers)).json()
        assert [item["language"] for item in body["items"]] == ["en"]
