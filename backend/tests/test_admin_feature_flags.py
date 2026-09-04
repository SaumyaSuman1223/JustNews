"""Integration tests for the admin feature-flag console, and for the one
real consumer wired to it: the Stage 5 heuristic-ranker kill switch.

The test database is built from SQLAlchemy metadata
(justnews_testing.fixtures), not by running Alembic migrations - so
0011_feature_flags's own seed INSERT never lands here. Tests that need the
``heuristic_ranker`` row to already exist seed it themselves via
``_seed_ranker_flag``, mirroring what that migration does in real
environments.
"""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services.feed import CHRONOLOGICAL_POLICY, HEURISTIC_POLICY
from justnews_core.db import set_current_user
from justnews_core.models import AdminAuditLog, FeatureFlag, Impression


async def _seed_ranker_flag(session: AsyncSession, *, enabled: bool = True) -> None:
    session.add(
        FeatureFlag(
            key="heuristic_ranker", enabled=enabled, description="Serve the heuristic ranker."
        )
    )
    await session.commit()


class TestListFeatureFlags:
    async def test_lists_an_existing_flag(self, client: AsyncClient, session: AsyncSession) -> None:
        await _seed_ranker_flag(session)

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/feature-flags", headers=admin)

        assert response.status_code == 200
        by_key = {row["key"]: row for row in response.json()}
        assert by_key["heuristic_ranker"]["enabled"] is True

    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        reader = await make_beta_headers(session)
        response = await client.get("/v1/admin/feature-flags", headers=reader)
        assert response.status_code == 403


class TestCreateFeatureFlag:
    async def test_creates_a_flag_and_writes_an_audit_log_entry(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            "/v1/admin/feature-flags",
            json={"key": "new_thing", "description": "A thing being rolled out.", "enabled": False},
            headers=admin,
        )
        assert response.status_code == 201
        assert response.json()["enabled"] is False

        audit_rows = (
            (
                await session.execute(
                    select(AdminAuditLog).where(AdminAuditLog.action == "feature_flag.create")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_rows) == 1
        assert audit_rows[0].target_id == "new_thing"

    async def test_rejects_a_malformed_key(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            "/v1/admin/feature-flags",
            json={"key": "Not Valid!", "description": "x"},
            headers=admin,
        )
        assert response.status_code == 422

    async def test_rejects_a_duplicate_key(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _seed_ranker_flag(session)

        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            "/v1/admin/feature-flags",
            json={"key": "heuristic_ranker", "description": "x"},
            headers=admin,
        )
        assert response.status_code == 422


class TestSetFeatureFlag:
    async def test_toggles_the_flag_and_writes_an_audit_log_entry(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _seed_ranker_flag(session)

        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            "/v1/admin/feature-flags/heuristic_ranker", json={"enabled": False}, headers=admin
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

        flag = await session.get(FeatureFlag, "heuristic_ranker")
        assert flag is not None
        assert flag.enabled is False

    async def test_a_missing_flag_404s(self, client: AsyncClient, session: AsyncSession) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            "/v1/admin/feature-flags/does_not_exist", json={"enabled": True}, headers=admin
        )
        assert response.status_code == 404


class TestHeuristicRankerKillSwitch:
    async def test_disabling_the_flag_forces_every_reader_to_chronological(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _seed_ranker_flag(session)
        source = await make_source(session)
        await make_article(session, source, title="A")
        await make_article(session, source, title="B")
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        await client.put(
            "/v1/admin/feature-flags/heuristic_ranker", json={"enabled": False}, headers=admin
        )

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 200

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows, "the fallback-served page must still log impressions"
        assert all(row.ranking_policy == CHRONOLOGICAL_POLICY for row in rows)

    async def test_a_missing_flag_row_defaults_to_enabled(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # No _seed_ranker_flag call here - this proves the fail-open default
        # for a key with no row at all, not the explicit-off path above.
        source = await make_source(session)
        await make_article(session, source, title="A")
        await make_article(session, source, title="B")
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 200

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(row.ranking_policy == HEURISTIC_POLICY for row in rows)
