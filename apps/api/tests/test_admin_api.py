"""Integration tests for the admin console API."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession


class TestAdminAccessControl:
    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session, role="reader")
        response = await client.get("/v1/admin/sources", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_an_admin_is_allowed(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/sources", headers=headers)
        assert response.status_code == 200


class TestModeration:
    async def test_takedown_hides_the_article_everywhere(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Bad article")
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        takedown = await client.post(
            f"/v1/admin/articles/{article.id}/takedown",
            json={"reason": "copyright complaint"},
            headers=admin,
        )
        assert takedown.status_code == 200

        public_view = await client.get(f"/v1/articles/{article.id}")
        assert public_view.status_code == 404

        listing = await client.get("/v1/articles")
        assert article.id not in [item["id"] for item in listing.json()["items"]]

    async def test_takedown_requires_a_reason(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            f"/v1/admin/articles/{article.id}/takedown", json={"reason": ""}, headers=admin
        )
        assert response.status_code == 422

    async def test_restore_makes_it_visible_again(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        await client.post(
            f"/v1/admin/articles/{article.id}/takedown", json={"reason": "test"}, headers=admin
        )
        restore = await client.post(f"/v1/admin/articles/{article.id}/restore", headers=admin)
        assert restore.status_code == 200

        public_view = await client.get(f"/v1/articles/{article.id}")
        assert public_view.status_code == 200

    async def test_list_removed_articles(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Removed")
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        await client.post(
            f"/v1/admin/articles/{article.id}/takedown", json={"reason": "test"}, headers=admin
        )
        removed = await client.get("/v1/admin/articles/removed", headers=admin)
        assert [item["title"] for item in removed.json()] == ["Removed"]

    async def test_taking_down_an_unknown_article_is_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            "/v1/admin/articles/999999/takedown", json={"reason": "test"}, headers=admin
        )
        assert response.status_code == 404


class TestOpsHealth:
    async def test_source_health_reports_article_counts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session, slug="health-check")
        await make_article(session, source)
        await make_article(session, source)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/sources", headers=admin)
        row = next(r for r in response.json() if r["slug"] == "health-check")
        assert row["article_count"] == 2

    async def test_ingest_runs_list_is_reachable(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/ingest-runs", headers=admin)
        assert response.status_code == 200
        assert response.json() == []


class TestUserAdmin:
    async def test_list_users_and_promote_to_admin(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        reader_headers = await make_beta_headers(session, role="reader")

        listing = await client.get("/v1/admin/users", headers=admin)
        assert listing.status_code == 200
        assert len(listing.json()) >= 2

        me = await client.get("/v1/me", headers=reader_headers)
        target_id = me.json()["id"]

        promote = await client.post(
            f"/v1/admin/users/{target_id}/role", json={"role": "admin"}, headers=admin
        )
        assert promote.status_code == 204

        again = await client.get("/v1/me", headers=reader_headers)
        assert again.json()["role"] == "admin"

    async def test_invalid_role_is_rejected(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.post(
            f"/v1/admin/users/{'0' * 8}-0000-0000-0000-{'0' * 12}/role",
            json={"role": "superuser"},
            headers=admin,
        )
        assert response.status_code == 422


class TestAnalytics:
    async def test_overview_is_reachable_and_shaped(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/analytics/overview", headers=admin)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "since",
            "active_users",
            "ctr_by_surface",
            "top_articles",
            "top_sources",
        }

    async def test_active_users_counts_a_feed_visit(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source)
        await session.commit()

        reader = await make_beta_headers(session)
        await client.get("/v1/feed", headers=reader)

        admin = await make_beta_headers(session, role="admin")
        overview = await client.get("/v1/admin/analytics/overview", headers=admin)
        assert overview.json()["active_users"] >= 1


class TestAuditLog:
    async def test_a_takedown_is_audit_logged(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        await client.post(
            f"/v1/admin/articles/{article.id}/takedown",
            json={"reason": "audit test"},
            headers=admin,
        )
        log = await client.get("/v1/admin/audit-log", headers=admin)
        actions = [entry["action"] for entry in log.json()]
        assert "article.takedown" in actions


class TestInvites:
    async def test_create_and_list_invites(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        created = await client.post(
            "/v1/admin/invites", json={"note": "batch 1", "max_uses": 5}, headers=admin
        )
        assert created.status_code == 201
        code = created.json()["code"]

        listing = await client.get("/v1/admin/invites", headers=admin)
        assert code in [item["code"] for item in listing.json()]

    async def test_a_new_reader_can_redeem_a_created_code(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        admin = await make_beta_headers(session, role="admin")
        created = await client.post("/v1/admin/invites", json={"max_uses": 1}, headers=admin)
        code = created.json()["code"]

        from justnews_testing.auth import make_access_token

        reader_headers = {"authorization": f"Bearer {make_access_token()}"}
        redeem = await client.post(
            "/v1/invites/redeem", json={"code": code}, headers=reader_headers
        )
        assert redeem.status_code == 204

        feed = await client.get("/v1/feed", headers=reader_headers)
        assert feed.status_code == 200

    async def test_a_code_cannot_be_redeemed_more_than_max_uses(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from justnews_testing.auth import make_access_token

        admin = await make_beta_headers(session, role="admin")
        created = await client.post("/v1/admin/invites", json={"max_uses": 1}, headers=admin)
        code = created.json()["code"]

        first_reader = {"authorization": f"Bearer {make_access_token()}"}
        second_reader = {"authorization": f"Bearer {make_access_token()}"}
        await client.post("/v1/invites/redeem", json={"code": code}, headers=first_reader)
        second = await client.post("/v1/invites/redeem", json={"code": code}, headers=second_reader)
        assert second.status_code == 409
