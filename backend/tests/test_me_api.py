"""Integration tests for authentication and the /me profile route."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.auth import make_access_token


class TestAuthentication:
    async def test_missing_token_is_401_in_the_standard_envelope(self, client: AsyncClient) -> None:
        response = await client.get("/v1/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"

    async def test_garbage_token_is_401(self, client: AsyncClient) -> None:
        response = await client.get("/v1/me", headers={"authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    async def test_wrong_audience_is_401(self, client: AsyncClient) -> None:
        token = make_access_token(audience="some-other-app")
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 401

    async def test_expired_token_is_401(self, client: AsyncClient) -> None:
        token = make_access_token(expires_in=-60)
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 401


class TestMe:
    async def test_first_request_creates_the_profile(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.get("/v1/me", headers={"authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["preferred_languages"] == []

    async def test_updates_preferred_languages(self, client: AsyncClient) -> None:
        token = make_access_token()
        headers = {"authorization": f"Bearer {token}"}
        response = await client.patch(
            "/v1/me", json={"preferred_languages": ["en", "es", "en"]}, headers=headers
        )
        assert response.status_code == 200
        # Deduplicated, order preserved.
        assert response.json()["preferred_languages"] == ["en", "es"]

        # And it sticks.
        again = await client.get("/v1/me", headers=headers)
        assert again.json()["preferred_languages"] == ["en", "es"]

    async def test_rejects_an_invalid_language(self, client: AsyncClient) -> None:
        token = make_access_token()
        response = await client.patch(
            "/v1/me",
            json={"preferred_languages": ["zzzz9"]},
            headers={"authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    async def test_each_user_sees_only_their_own_profile(self, client: AsyncClient) -> None:
        alice = make_access_token()
        bob = make_access_token()
        await client.patch(
            "/v1/me",
            json={"preferred_languages": ["ar"]},
            headers={"authorization": f"Bearer {alice}"},
        )

        bob_profile = await client.get("/v1/me", headers={"authorization": f"Bearer {bob}"})
        assert bob_profile.json()["preferred_languages"] == []
