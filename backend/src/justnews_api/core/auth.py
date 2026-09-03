"""Wires Supabase JWT verification into FastAPI's dependency system."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from justnews_api.services.auth import JWKSProvider, Principal, verify_jwt
from justnews_core.errors import AuthenticationError
from justnews_core.settings import get_settings

# auto_error=False: a missing header should raise our own AuthenticationError
# (and go through the standard error envelope), not FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)


def _jwks_provider(request: Request) -> JWKSProvider:
    provider: JWKSProvider | None = getattr(request.app.state, "jwks_provider", None)
    if provider is None:
        raise RuntimeError("jwks_provider was not initialised at startup")
    return provider


async def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    """For routes only a signed-in reader may use: saves, follows, history,
    /me, personalised /feed."""
    if credentials is None:
        raise AuthenticationError("A bearer token is required.")
    return await verify_jwt(
        credentials.credentials, provider=_jwks_provider(request), settings=get_settings()
    )


async def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal | None:
    """For routes that work for both logged-out exploration and signed-in
    readers, such as impression logging on the public feed surfaces."""
    if credentials is None:
        return None
    return await verify_jwt(
        credentials.credentials, provider=_jwks_provider(request), settings=get_settings()
    )
