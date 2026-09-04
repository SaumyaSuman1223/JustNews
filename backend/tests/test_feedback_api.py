"""Integration tests for the feedback widget: submission (gated by the beta
invite, same as every other write path) and the admin read side."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from sqlalchemy.ext.asyncio import AsyncSession


class TestSubmitFeedback:
    async def test_a_beta_reader_can_submit_feedback(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/feedback",
            json={
                "message": "The search page is slow on my phone.",
                "locale": "en",
                "path": "/en/search",
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["id"] > 0

    async def test_rejects_an_empty_message(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/feedback", json={"message": "   ", "locale": "en"}, headers=headers
        )
        assert response.status_code == 422

    async def test_rejects_an_oversized_message(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/feedback", json={"message": "x" * 2001, "locale": "en"}, headers=headers
        )
        assert response.status_code == 422

    async def test_a_reader_without_a_redeemed_invite_is_forbidden(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session, redeem_invite=False)
        response = await client.post(
            "/v1/feedback", json={"message": "Hello", "locale": "en"}, headers=headers
        )
        assert response.status_code == 403


class TestAdminFeedback:
    async def test_an_admin_reads_submitted_feedback(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        reader = await make_beta_headers(session)
        await client.post(
            "/v1/feedback",
            json={"message": "Loved the new onboarding.", "locale": "en"},
            headers=reader,
        )

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/feedback", headers=admin)

        assert response.status_code == 200
        messages = [row["message"] for row in response.json()]
        assert "Loved the new onboarding." in messages

    async def test_a_reader_is_forbidden_from_the_admin_list(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        reader = await make_beta_headers(session)
        response = await client.get("/v1/admin/feedback", headers=reader)
        assert response.status_code == 403
