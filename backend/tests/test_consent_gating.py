"""Integration tests for consent-gated impression logging.

Confirmed scope (see frontend/lib/consent.ts and the Stage 4 plan): consent
gates *observation* - impressions, the /v1/feed and /v1/explore surfaces -
not *preference*. "Not interested" and its undo stay working unconditionally
regardless of the x-analytics-consent header, because they are the reader's
own deliberate instruction, not passive tracking.
"""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.feed import CHRONOLOGICAL_POLICY
from justnews_core.db import set_current_user
from justnews_core.models import Impression


async def _chronological_headers(session: AsyncSession) -> dict[str, str]:
    return await make_beta_headers(session, user_id=find_user_id_for_policy(CHRONOLOGICAL_POLICY))


class TestFeedImpressionGating:
    async def test_no_impression_rows_without_the_consent_header(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await session.commit()

        user_id = find_user_id_for_policy(CHRONOLOGICAL_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        body = (await client.get("/v1/feed", headers=headers)).json()

        assert body["items"][0]["impression_id"] is None
        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows == []

    async def test_impression_rows_written_once_consent_is_granted(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await session.commit()

        user_id = find_user_id_for_policy(CHRONOLOGICAL_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        body = (await client.get("/v1/feed", headers=headers)).json()

        assert isinstance(body["items"][0]["impression_id"], int)
        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert len(rows) == 1

    async def test_a_value_other_than_granted_still_fails_closed(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await session.commit()

        headers = await _chronological_headers(session)
        headers["x-analytics-consent"] = "true"  # not the literal string "granted"
        body = (await client.get("/v1/feed", headers=headers)).json()
        assert body["items"][0]["impression_id"] is None


class TestExploreImpressionGating:
    async def test_anonymous_visitor_without_consent_generates_no_impressions(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await session.commit()

        body = (await client.get("/v1/explore")).json()
        assert body["items"][0]["impression_id"] is None

    async def test_anonymous_visitor_with_consent_generates_impressions(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await session.commit()

        body = (await client.get("/v1/explore", headers={"x-analytics-consent": "granted"})).json()
        assert isinstance(body["items"][0]["impression_id"], int)


class TestPreferenceUnaffectedByConsent:
    """ "Not interested" and undo are deliberately not gated - see the module
    docstring. No x-analytics-consent header is sent at all in either test,
    which is itself the point: these must not require one."""

    async def test_not_interested_works_with_no_consent_header(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/not-interested",
            json={"article_id": article.id, "surface": "feed"},
            headers=headers,
        )
        assert response.status_code == 204

    async def test_undo_works_with_no_consent_header(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        headers = await make_beta_headers(session)
        await client.post(
            "/v1/not-interested",
            json={"article_id": article.id, "surface": "feed"},
            headers=headers,
        )
        response = await client.delete(
            f"/v1/not-interested/{article.id}", params={"surface": "feed"}, headers=headers
        )
        assert response.status_code == 204
