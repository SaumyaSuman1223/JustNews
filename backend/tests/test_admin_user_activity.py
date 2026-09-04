"""Integration tests for the admin "watch a session" debugging view - a
merged, chronological timeline of one reader's impressions and interactions."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import AdminAuditLog, Impression, InteractionEvent


class TestUserActivity:
    async def test_merges_impressions_and_interactions_most_recent_first(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Watched article")
        await session.commit()

        user_id = uuid.uuid4()
        await make_beta_headers(session, user_id=str(user_id))
        session.add(
            Impression(
                user_id=user_id,
                session_id="s",
                article_id=article.id,
                position=0,
                surface="feed",
                locale="en",
                propensity=1.0,
                ranking_policy="heuristic_v1",
            )
        )
        await session.commit()
        session.add(
            InteractionEvent(
                user_id=user_id,
                session_id="s",
                article_id=article.id,
                event_type="click",
                surface="feed",
                locale="en",
            )
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get(f"/v1/admin/users/{user_id}/activity", headers=admin)

        assert response.status_code == 200
        kinds = [row["kind"] for row in response.json()]
        assert set(kinds) == {"impression", "interaction"}
        # Most recent first - the interaction was written after the
        # impression, so it should lead.
        assert kinds[0] == "interaction"

    async def test_writes_an_audit_log_entry(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        user_id = uuid.uuid4()
        await make_beta_headers(session, user_id=str(user_id))

        admin = await make_beta_headers(session, role="admin")
        await client.get(f"/v1/admin/users/{user_id}/activity", headers=admin)

        rows = (
            (
                await session.execute(
                    select(AdminAuditLog).where(AdminAuditLog.action == "user.view_activity")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].target_id == str(user_id)

    async def test_an_unknown_user_404s(self, client: AsyncClient, session: AsyncSession) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.get(f"/v1/admin/users/{uuid.uuid4()}/activity", headers=admin)
        assert response.status_code == 404

    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        reader = await make_beta_headers(session)
        response = await client.get(f"/v1/admin/users/{uuid.uuid4()}/activity", headers=reader)
        assert response.status_code == 403
