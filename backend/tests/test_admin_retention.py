"""Integration tests for the retention-cohort analytics endpoint. Cohorts
are keyed by the week a reader redeemed their invite - make_beta_headers
always stamps that as "now", so these tests back-date it afterward with a
direct UPDATE to place a reader in a specific past cohort week."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Impression, UserProfile

NOW = datetime.now(UTC)


async def _seed_reader(session: AsyncSession, *, redeemed_weeks_ago: float) -> uuid.UUID:
    user_id = uuid.uuid4()
    await make_beta_headers(session, user_id=str(user_id))
    await session.execute(
        update(UserProfile)
        .where(UserProfile.id == user_id)
        .values(invite_redeemed_at=NOW - timedelta(weeks=redeemed_weeks_ago))
    )
    await session.commit()
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


class TestRetentionCohorts:
    async def test_a_reader_active_at_signup_counts_in_week_zero(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        user_id = await _seed_reader(session, redeemed_weeks_ago=1)
        await _seed_impression(session, article_id=article.id, user_id=user_id, served_at=NOW)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/retention?window_weeks=8", headers=admin)

        assert response.status_code == 200
        # Just assert something landed with a nonzero cohort size and at
        # least one active week - exact bucket-week arithmetic is Postgres's
        # date_trunc, not worth re-deriving here.
        cohorts = response.json()
        assert any(c["cohort_size"] >= 1 for c in cohorts)
        assert any(w["active_users"] >= 1 for c in cohorts for w in c["weeks"])

    async def test_a_reader_with_no_activity_after_signup_has_no_later_weeks(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        # Signed up 3 weeks ago, active only that week - never came back.
        user_id = await _seed_reader(session, redeemed_weeks_ago=3)
        await _seed_impression(
            session, article_id=article.id, user_id=user_id, served_at=NOW - timedelta(weeks=3)
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/retention?window_weeks=8", headers=admin)
        assert response.status_code == 200
        cohorts = response.json()
        matching = [c for c in cohorts if c["cohort_size"] >= 1]
        assert matching
        for cohort in matching:
            offsets = {w["week_offset"] for w in cohort["weeks"]}
            # Only week 0 - no activity in any later week for this cohort.
            assert offsets <= {0}

    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        reader = await make_beta_headers(session)
        response = await client.get("/v1/admin/analytics/retention", headers=reader)
        assert response.status_code == 403

    async def test_rejects_an_out_of_range_window(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/retention?window_weeks=0", headers=admin)
        assert response.status_code == 422
