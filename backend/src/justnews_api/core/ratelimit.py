"""Per-minute rate limiting via Upstash's REST API.

Upstash, not a persistent Redis connection: the free-tier API host spins down
between requests, so a Redis connection pool has nothing to sit on between
them. A REST call per request is the shape that works here - over one
keep-alive HTTPS client (core/upstash.py), not a new one per call, which paid
a fresh TCP and TLS handshake before every request did any work.

Degrades to a no-op when Upstash is not configured - the default in local dev
and CI, where requiring a paid external dependency just to run `pytest` would
be its own kind of bug.
"""

from __future__ import annotations

import hmac
import time
from collections.abc import Awaitable, Callable

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from justnews_api.core import upstash
from justnews_core.logging import get_logger
from justnews_core.settings import Settings

log = get_logger(__name__)

_EXEMPT_PATHS = frozenset({"/health", "/health/ready"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._settings = settings
        self._enabled = upstash.is_configured(settings)
        if not self._enabled:
            log.warning("rate_limiting_disabled", reason="Upstash is not configured")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self._enabled or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)
        if self._is_web_tier(request):
            return await call_next(request)

        identity = _client_identity(request)
        window = int(time.time() // 60)
        key = f"ratelimit:{identity}:{window}"

        try:
            count = await self._increment(key)
        except httpx.HTTPError as exc:
            # Upstash being unreachable must not take the API down with it -
            # fail open, the same reasoning as every other degraded mode here.
            log.warning("rate_limit_check_failed", error=str(exc))
            return await call_next(request)

        if count > self._settings.rate_limit_requests_per_minute:
            log.warning("rate_limited", identity=identity, count=count)
            request_id = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60"},
                content={
                    "error": {
                        "code": "quota_exceeded",
                        "message": "Too many requests. Try again shortly.",
                        "request_id": request_id,
                    }
                },
            )
        return await call_next(request)

    def _is_web_tier(self, request: Request) -> bool:
        """The web server's own anonymous reads, identified by the shared key.

        Only anonymous ones: a request with a bearer token is still limited
        by its token, whoever forwarded it.
        """
        secret = self._settings.web_proxy_secret
        offered = request.headers.get("x-web-proxy-key")
        if not secret or not offered or request.headers.get("authorization"):
            return False
        return hmac.compare_digest(offered.encode(), secret.encode())

    async def _increment(self, key: str) -> int:
        results = await upstash.pipeline(self._settings, [["INCR", key], ["EXPIRE", key, "60"]])
        return int(results[0])


def _client_identity(request: Request) -> str:
    """The bearer token's suffix if there is one, else the client IP.

    Not JWT-verified here - this middleware runs before auth and only needs a
    stable bucket key, not a real identity. A per-token limit is what
    protects an authenticated surface from a single compromised token; a
    per-IP limit is what protects anonymous exploration.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[len("bearer ") :].strip()
        return f"token:{token[-24:]}"
    return f"ip:{request.client.host}" if request.client else "ip:unknown"
