"""Integration tests for the DAU/WAU admin analytics endpoints. Rows are
seeded directly with explicit `served_at`/`created_at` timestamps - the
ordinary logging path always stamps "now", and these tests need to place
activity into known day and week buckets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Impression, InteractionEvent

NOW = datetime.now(UTC)


async def _seed_user(session: AsyncSession) -> uuid.UUID:
    # Impressions/interactions FK to user_profiles, so a row must exist there
    # first - make_beta_headers is the established way to mint one in tests.
    user_id = uuid.uuid4()
    await make_beta_headers(session, user_id=str(user_id))
    return user_id


async def _seed_impression(
    session: AsyncSession, *, article_id: int, user_id: uuid.UUID, served_at: datetime
) -> None:
    session.add(
        Impression(
            user_id=user_id,
            session_id="s",
            article_id=article_id,
            position=1,
            surface="feed",
            locale="en",
            propensity=1.0,
            ranking_policy="chronological_v0",
            served_at=served_at,
        )
    )


class TestDailyActiveUsers:
    async def test_counts_distinct_users_per_day_bucket(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        today_users = [await _seed_user(session) for _ in range(2)]
        yesterday_user = await _seed_user(session)
        for user_id in today_users:
            await _seed_impression(session, article_id=article.id, user_id=user_id, served_at=NOW)
        await _seed_impression(
            session,
            article_id=article.id,
            user_id=yesterday_user,
            served_at=NOW - timedelta(days=1),
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/dau?window_days=7", headers=admin)

        assert response.status_code == 200
        by_bucket = {row["bucket"][:10]: row["active_users"] for row in response.json()}
        assert by_bucket[NOW.date().isoformat()] == 2
        assert by_bucket[(NOW - timedelta(days=1)).date().isoformat()] == 1

    async def test_a_user_impressed_and_interacted_the_same_day_counts_once(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        user_id = await _seed_user(session)
        await _seed_impression(session, article_id=article.id, user_id=user_id, served_at=NOW)
        session.add(
            InteractionEvent(
                user_id=user_id,
                session_id="s",
                article_id=article.id,
                event_type="click",
                surface="feed",
                locale="en",
                created_at=NOW,
            )
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/dau?window_days=7", headers=admin)

        by_bucket = {row["bucket"][:10]: row["active_users"] for row in response.json()}
        assert by_bucket[NOW.date().isoformat()] == 1


class TestWeeklyActiveUsers:
    async def test_counts_distinct_users_per_week_bucket(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        user_id = await _seed_user(session)
        await _seed_impression(session, article_id=article.id, user_id=user_id, served_at=NOW)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/wau?window_weeks=4", headers=admin)

        assert response.status_code == 200
        assert sum(row["active_users"] for row in response.json()) == 1

    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        reader = await make_beta_headers(session, role="reader")
        response = await client.get("/v1/admin/analytics/dau", headers=reader)
        assert response.status_code == 403
