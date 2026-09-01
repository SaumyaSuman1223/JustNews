"""Integration tests for the private-beta invite gate."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token
from justnews_testing.beta import make_beta_headers
from sqlalchemy.ext.asyncio import AsyncSession


class TestBetaGate:
    async def test_a_reader_without_an_invite_is_blocked_from_the_feed(
        self, client: AsyncClient
    ) -> None:
        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_me_works_without_an_invite(self, client: AsyncClient) -> None:
        # /v1/me must stay reachable - it is how a reader finds out they need
        # one, and how they redeem it.
        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.get("/v1/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["has_beta_access"] is False

    async def test_a_redeemed_invite_unlocks_the_feed(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 200

    async def test_me_reports_beta_access_after_redemption(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.get("/v1/me", headers=headers)
        assert response.json()["has_beta_access"] is True

    async def test_redeeming_an_unknown_code_is_404(self, client: AsyncClient) -> None:
        headers = {"authorization": f"Bearer {make_access_token()}"}
        response = await client.post(
            "/v1/invites/redeem", json={"code": "no-such-code"}, headers=headers
        )
        assert response.status_code == 404

    async def test_redeeming_twice_is_a_conflict(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/invites/redeem", json={"code": "anything"}, headers=headers
        )
        assert response.status_code == 409

    async def test_admin_bypasses_the_gate_without_redeeming(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        headers = await make_beta_headers(session, role="admin", redeem_invite=False)
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 200
