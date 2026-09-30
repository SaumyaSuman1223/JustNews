"""The logging a learned ranker trains on (ADR 0015): which served cards were
seen (POST /v1/impressions/views), and clicks from any reader, signed in or
not (POST /v1/clicks)."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article, Impression, ImpressionView, InteractionEvent

CONSENTED = {"x-analytics-consent": "granted", "x-session-id": "anon-1"}


async def _impression(
    session: AsyncSession,
    article: Article,
    *,
    session_id: str = "anon-1",
    user_id: uuid.UUID | None = None,
    position: int = 0,
) -> int:
    row = Impression(
        user_id=user_id,
        session_id=session_id,
        article_id=article.id,
        position=position,
        surface="top",
        locale="en",
        propensity=0.5,
        ranking_policy="heuristic_v2",
    )
    session.add(row)
    await session.flush()
    await session.commit()
    return row.id


class TestViews:
    async def test_records_a_view_of_ones_own_impression(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        impression_id = await _impression(session, article)

        response = await client.post(
            "/v1/impressions/views",
            json={
                "views": [{"impression_id": impression_id, "rendered_position": 3, "slot": "card"}]
            },
            headers=CONSENTED,
        )
        assert response.status_code == 204
        view = (await session.execute(select(ImpressionView))).scalar_one()
        assert (view.impression_id, view.rendered_position, view.slot) == (impression_id, 3, "card")

    async def test_ignores_another_sessions_impression(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        theirs = await _impression(session, article, session_id="someone-else")

        await client.post(
            "/v1/impressions/views",
            json={"views": [{"impression_id": theirs, "rendered_position": 0, "slot": "lead"}]},
            headers=CONSENTED,
        )
        assert (await session.execute(select(ImpressionView))).first() is None

    async def test_a_second_view_of_the_same_card_is_one_view(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        impression_id = await _impression(session, article)
        body = {"views": [{"impression_id": impression_id, "rendered_position": 0, "slot": "lead"}]}

        await client.post("/v1/impressions/views", json=body, headers=CONSENTED)
        again = await client.post("/v1/impressions/views", json=body, headers=CONSENTED)
        assert again.status_code == 204
        assert len((await session.execute(select(ImpressionView))).all()) == 1

    async def test_nothing_is_recorded_without_consent(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        impression_id = await _impression(session, article)

        await client.post(
            "/v1/impressions/views",
            json={
                "views": [{"impression_id": impression_id, "rendered_position": 0, "slot": "card"}]
            },
            headers={"x-session-id": "anon-1"},
        )
        assert (await session.execute(select(ImpressionView))).first() is None

    async def test_an_unknown_slot_is_rejected(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        impression_id = await _impression(session, article)

        response = await client.post(
            "/v1/impressions/views",
            json={
                "views": [{"impression_id": impression_id, "rendered_position": 0, "slot": "hero"}]
            },
            headers=CONSENTED,
        )
        assert response.status_code == 422

    async def test_a_signed_in_readers_views_are_matched_by_account(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        user_id = uuid.uuid4()
        headers = await make_beta_headers(session, user_id=str(user_id))
        impression_id = await _impression(session, article, session_id="other-tab", user_id=user_id)

        await client.post(
            "/v1/impressions/views",
            json={
                "views": [{"impression_id": impression_id, "rendered_position": 0, "slot": "row"}]
            },
            headers={**headers, **CONSENTED},
        )
        assert (await session.execute(select(ImpressionView))).scalar_one().slot == "row"


class TestClicks:
    async def test_a_signed_out_click_counts_against_its_impression(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session), language="es")
        impression_id = await _impression(session, article, position=4)

        response = await client.post(
            "/v1/clicks",
            json={
                "article_id": article.id,
                "surface": "top",
                "position": 4,
                "impression_id": impression_id,
                "locale": "en",
            },
            headers=CONSENTED,
        )
        assert response.status_code == 204
        event = (await session.execute(select(InteractionEvent))).scalar_one()
        assert event.user_id is None
        assert event.session_id == "anon-1"
        assert event.impression_id == impression_id
        # The interface language, not the article's.
        assert event.locale == "en"

    async def test_a_signed_out_click_without_its_impression_is_dropped(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        theirs = await _impression(session, article, session_id="someone-else")

        for impression_id in (None, theirs):
            await client.post(
                "/v1/clicks",
                json={"article_id": article.id, "surface": "top", "impression_id": impression_id},
                headers=CONSENTED,
            )
        assert (await session.execute(select(InteractionEvent))).first() is None

    async def test_a_signed_in_reader_without_an_invite_is_recorded(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        await session.commit()
        token = make_access_token()

        response = await client.post(
            "/v1/clicks",
            json={"article_id": article.id, "surface": "search"},
            headers={"authorization": f"Bearer {token}", **CONSENTED},
        )
        assert response.status_code == 204
        event = (await session.execute(select(InteractionEvent))).scalar_one()
        assert event.user_id is not None

    async def test_nothing_is_recorded_without_consent(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        await session.commit()
        headers = await make_beta_headers(session)

        await client.post(
            "/v1/clicks", json={"article_id": article.id, "surface": "feed"}, headers=headers
        )
        assert (await session.execute(select(InteractionEvent))).first() is None

    async def test_aquila_is_a_click_surface(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        article = await make_article(session, await make_source(session))
        await session.commit()
        headers = await make_beta_headers(session)

        response = await client.post(
            "/v1/clicks",
            json={"article_id": article.id, "surface": "aquila"},
            headers={**headers, **CONSENTED},
        )
        assert response.status_code == 204
