"""Test helper for the private-beta invite gate (Stage 4).

Everything behind ``core.db.get_beta_session`` - the feed, saves, follows,
history, not-interested - now 403s an authenticated caller who has not
redeemed an invite. Most integration tests for those routes are not testing
the invite flow itself, so this grants access directly against the database,
the same reasoning ``make_article`` uses to bypass ingestion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import set_current_user
from justnews_core.models import UserProfile
from justnews_testing.auth import make_access_token


async def make_beta_headers(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    role: str = "reader",
    redeem_invite: bool = True,
) -> dict[str, str]:
    """A bearer-token header for a reader who has already redeemed an invite.

    ``redeem_invite=False`` leaves the profile un-redeemed - for testing that
    an admin role bypasses the gate on its own, without the redemption also
    being sufficient on its own.
    """
    token = make_access_token(user_id=user_id)
    # No signature check needed - this is our own just-minted test token, not
    # one from an untrusted source.
    claims = jwt.decode(token, options={"verify_signature": False})
    uid = str(claims["sub"])

    await set_current_user(session, uid)
    profile = await session.get(UserProfile, UUID(uid))
    redeemed_at = datetime.now(UTC) if redeem_invite else None
    if profile is None:
        profile = UserProfile(
            id=UUID(uid), invite_redeemed_at=redeemed_at, redeemed_invite_code="test", role=role
        )
        session.add(profile)
    else:
        profile.invite_redeemed_at = redeemed_at
        profile.role = role
    await session.flush()
    await session.commit()

    return {"authorization": f"Bearer {token}"}
