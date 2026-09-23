"""One long-lived HTTPS client for Upstash's REST API.

Upstash is reached over REST, not a Redis connection (see core/ratelimit.py
for why). Before this module, every call opened a fresh ``httpx.AsyncClient``
- a new TCP connection and TLS handshake on every API request, paid before
the request did any work. One client per process keeps the connection alive
between calls, so a command costs one round trip instead of three.

Opened lazily and closed from the app's lifespan. Every function here returns
``None`` or raises ``httpx.HTTPError``; callers decide what degrading means.
"""

from __future__ import annotations

from typing import Any

import httpx

from justnews_core.settings import Settings

#: Upstash is a cache and a counter, never the source of truth. A slow answer
#: is worth less than no answer: the caller falls back to the database.
UPSTASH_TIMEOUT_SECONDS = 0.6

_client: httpx.AsyncClient | None = None


def is_configured(settings: Settings) -> bool:
    return bool(settings.upstash_redis_rest_url and settings.upstash_redis_rest_token)


def _get_client(settings: Settings) -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=str(settings.upstash_redis_rest_url),
            headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
            timeout=UPSTASH_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_keepalive_connections=10, keepalive_expiry=60),
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def pipeline(settings: Settings, commands: list[list[str]]) -> list[Any]:
    """Run commands in one round trip; returns each command's ``result``.

    No retry: every caller has a cheaper fallback than a second round trip
    (the database for the cache, the in-process count for the rate limiter).
    """
    response = await _get_client(settings).post("/pipeline", json=commands)
    response.raise_for_status()
    return [entry.get("result") for entry in response.json()]
