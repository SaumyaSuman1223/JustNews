"""Supabase JWT verification against its JWKS endpoint.

No FastAPI import here by design - this is business logic. ``core/auth.py``
is the thin layer that plugs it into request handling via ``Depends``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx
import jwt

from justnews_core.errors import AuthenticationError, UpstreamError
from justnews_core.logging import get_logger
from justnews_core.settings import Settings

log = get_logger(__name__)

_SUPPORTED_ALGORITHMS = ("RS256", "ES256")


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller. ``user_id`` is the Supabase auth user id -
    the only claim any repository is allowed to trust."""

    user_id: UUID
    email: str | None = None


class JWKSProvider(Protocol):
    async def get_signing_key(self, kid: str) -> jwt.PyJWK: ...


class SupabaseJWKSProvider:
    """Fetches and caches Supabase's JWKS.

    Refreshed on a TTL, and also on an unrecognised ``kid`` - so a real key
    rotation is picked up without waiting out the cache, while a client
    sending a bogus ``kid`` still cannot force a fetch on every request
    (the lock re-checks staleness before actually fetching).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_signing_key(self, kid: str) -> jwt.PyJWK:
        if kid not in self._keys or self._is_stale():
            await self._refresh()
        try:
            return self._keys[kid]
        except KeyError as exc:
            raise AuthenticationError("Token was signed with an unknown key.") from exc

    def _is_stale(self) -> bool:
        return time.monotonic() - self._fetched_at > self._settings.jwks_cache_seconds

    async def _refresh(self) -> None:
        async with self._lock:
            if self._keys and not self._is_stale():
                return  # another request refreshed while this one waited
            url = self._settings.supabase_jwks_url
            if url is None:
                raise AuthenticationError("Authentication is not configured.")
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.auth_http_timeout_seconds
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                log.error("jwks_fetch_failed", error=str(exc))
                raise UpstreamError("supabase_jwks", "Could not fetch signing keys.") from exc

            payload = response.json()
            self._keys = {jwk["kid"]: jwt.PyJWK(jwk) for jwk in payload.get("keys", [])}
            self._fetched_at = time.monotonic()


async def verify_jwt(token: str, *, provider: JWKSProvider, settings: Settings) -> Principal:
    """Verify a bearer token and return the principal it names.

    Every failure - malformed token, unsupported algorithm, expired, wrong
    audience, unknown key - collapses to the same ``AuthenticationError``.
    A caller with a bad token gets 401 either way, and the JWKS fetch is the
    only step that can legitimately be a 502 instead (``UpstreamError``,
    raised from ``provider.get_signing_key``).
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Malformed token.") from exc

    kid = header.get("kid")
    alg = header.get("alg")
    if not kid or alg not in _SUPPORTED_ALGORITHMS:
        raise AuthenticationError("Unsupported token.")

    signing_key = await provider.get_signing_key(kid)

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=[alg],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    try:
        user_id = UUID(str(claims["sub"]))
    except ValueError as exc:
        raise AuthenticationError("Token has no valid subject.") from exc

    return Principal(user_id=user_id, email=claims.get("email"))
