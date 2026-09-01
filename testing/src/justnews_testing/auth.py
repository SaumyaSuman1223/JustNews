"""JWT test helpers.

A self-signed RSA keypair stands in for Supabase's JWKS, so a test can mint a
real, verifiable token for any user id without a live Supabase project. The
key is generated once per test process - it is never meant to sign anything
outside this process.
"""

from __future__ import annotations

import json
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from jwt.algorithms import RSAAlgorithm

from justnews_core.errors import AuthenticationError

_KID = "test-key-1"
_PRIVATE_KEY: RSAPrivateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJWKSProvider:
    """Structurally matches ``justnews_api.services.auth.JWKSProvider`` - no
    network access, resolves the one key this module signs with."""

    async def get_signing_key(self, kid: str) -> jwt.PyJWK:
        if kid != _KID:
            raise AuthenticationError("Unknown signing key.")
        jwk_dict = json.loads(RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key()))
        jwk_dict["kid"] = _KID
        jwk_dict["alg"] = "RS256"
        return jwt.PyJWK(jwk_dict)


def make_access_token(
    user_id: str | None = None,
    *,
    audience: str = "authenticated",
    issuer: str | None = None,
    email: str | None = "reader@example.test",
    expires_in: int = 3600,
) -> str:
    """A token shaped like Supabase's, signed with this module's test key."""
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": user_id or str(uuid.uuid4()),
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
    }
    if issuer is not None:
        claims["iss"] = issuer
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KID})
