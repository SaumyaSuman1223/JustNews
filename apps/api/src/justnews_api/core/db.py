"""Per-request database session dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.repositories import users as users_repo
from justnews_api.services.auth import Principal
from justnews_core.db import get_session_factory, set_current_user


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
