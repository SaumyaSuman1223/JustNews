"""Unit tests for the Upstash-backed rate limit middleware.

No real Upstash here - ``_increment`` is monkeypatched, since the interesting
behaviour (429 over the limit, fail open on an Upstash error) lives entirely
in ``dispatch``, not in the REST call itself. ``BaseHTTPMiddleware`` is
itself a valid ASGI app, so it is driven directly through ``TestClient``
without needing a full Starlette router around it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from justnews_api.core.ratelimit import RateLimitMiddleware
from justnews_core.settings import Settings


async def _inner_app(scope: object, receive: object, send: object) -> None:
    response = PlainTextResponse("ok")
    await response(scope, receive, send)  # type: ignore[arg-type]


def _client(settings: Settings, increment: Callable[[str], Awaitable[int]]) -> TestClient:
    middleware = RateLimitMiddleware(_inner_app, settings=settings)
    middleware._increment = increment  # type: ignore[method-assign]
    return TestClient(middleware)


def _settings(limit: int = 10, web_proxy_secret: str | None = None) -> Settings:
    return Settings(  # type: ignore[call-arg]
        upstash_redis_rest_url="https://fake-upstash.example",
        upstash_redis_rest_token="fake-token",
        rate_limit_requests_per_minute=limit,
        web_proxy_secret=web_proxy_secret,
    )


class TestRateLimit:
    def test_disabled_when_upstash_is_not_configured(self) -> None:
        async def unreachable(key: str) -> int:
            raise AssertionError("should never be called when disabled")

        client = _client(Settings(), unreachable)  # type: ignore[call-arg]
        assert client.get("/thing").status_code == 200

    def test_allows_requests_under_the_limit(self) -> None:
        async def increment(key: str) -> int:
            return 1

        client = _client(_settings(limit=10), increment)
        assert client.get("/thing").status_code == 200

    def test_blocks_requests_over_the_limit(self) -> None:
        async def increment(key: str) -> int:
            return 11

        client = _client(_settings(limit=10), increment)
        response = client.get("/thing")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        assert response.json()["error"]["code"] == "quota_exceeded"

    def test_fails_open_when_upstash_is_unreachable(self) -> None:
        async def broken(key: str) -> int:
            raise httpx.ConnectError("no route to host")

        client = _client(_settings(limit=1), broken)
        assert client.get("/thing").status_code == 200

    def test_health_checks_are_exempt(self) -> None:
        async def increment(key: str) -> int:
            return 999  # would otherwise always be over any limit

        client = _client(_settings(limit=1), increment)
        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").status_code == 200

    def test_the_web_tier_is_not_limited_by_its_own_address(self) -> None:
        async def increment(key: str) -> int:
            return 999

        client = _client(_settings(limit=1, web_proxy_secret="s3cret"), increment)
        assert client.get("/thing", headers={"x-web-proxy-key": "s3cret"}).status_code == 200

    def test_a_wrong_proxy_key_is_limited_like_anyone(self) -> None:
        async def increment(key: str) -> int:
            return 999

        client = _client(_settings(limit=1, web_proxy_secret="s3cret"), increment)
        assert client.get("/thing", headers={"x-web-proxy-key": "guess"}).status_code == 429

    def test_a_proxy_key_does_not_exempt_a_bearer_token(self) -> None:
        async def increment(key: str) -> int:
            return 999

        client = _client(_settings(limit=1, web_proxy_secret="s3cret"), increment)
        response = client.get(
            "/thing", headers={"x-web-proxy-key": "s3cret", "authorization": "Bearer abc"}
        )
        assert response.status_code == 429

    def test_no_secret_configured_means_no_exemption(self) -> None:
        async def increment(key: str) -> int:
            return 999

        client = _client(_settings(limit=1), increment)
        assert client.get("/thing", headers={"x-web-proxy-key": ""}).status_code == 429
