"""Per-request database session dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.repositories import users as users_repo
from justnews_api.services.auth import Principal
from justnews_core.db import get_session_factory, set_current_user
from justnews_core.errors import AuthorizationError


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def get_user_session(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[AsyncSession]:
    """A transactional session for a signed-in reader's request.

    Sets ``app.user_id`` for RLS before anything else runs on this session,
    then commits on success and rolls back on any exception - the same
    contract as ``justnews_core.db.session_scope``, just per-request instead
    of standalone.

    Also ensures the reader's profile row exists. Every user-owned table -
    saves, follows, impressions - has a foreign key into ``user_profiles``,
    and a JWT is valid the moment Supabase issues it, well before anything
    here has seen that user. Without this, a token's very first write hits
    that foreign key instead of a row that was never created.
    """
    await set_current_user(session, str(principal.user_id))
    await users_repo.upsert_profile(session, principal.user_id)
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    else:
        await session.commit()


async def get_beta_session(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> AsyncIterator[AsyncSession]:
    """For routes only a reader who has redeemed a beta invite may use: the
    feed, saves, follows, history. An admin always passes, invited or not -
    they need to be able to see the product they operate.
    """
    profile = await users_repo.get_profile(session, principal.user_id)
    if profile is None or (profile.role != "admin" and profile.invite_redeemed_at is None):
        raise AuthorizationError("Redeem an invite code to unlock this.")
    yield session


async def get_admin_session(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_user_session),
) -> AsyncIterator[AsyncSession]:
    """For ``/v1/admin/*`` only. Every route behind this must itself write an
    ``AdminAuditLog`` row for the action it takes - this dependency only
    confirms the caller is allowed in, it does not log what they did once
    inside.
    """
    profile = await users_repo.get_profile(session, principal.user_id)
    if profile is None or profile.role != "admin":
        raise AuthorizationError("Admin access required.")
    yield session
