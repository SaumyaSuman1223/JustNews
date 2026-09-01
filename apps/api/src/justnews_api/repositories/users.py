from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import UserProfile


async def get_profile(session: AsyncSession, user_id: UUID) -> UserProfile | None:
    return await session.get(UserProfile, user_id)


async def upsert_profile(
    session: AsyncSession, user_id: UUID, *, preferred_languages: list[str] | None = None
) -> UserProfile:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(id=user_id, preferred_languages=preferred_languages or [])
        session.add(profile)
        await session.flush()
        return profile
    if preferred_languages is not None:
        profile.preferred_languages = preferred_languages
        await session.flush()
    return profile


async def mark_invite_redeemed(session: AsyncSession, user_id: UUID, code: str) -> None:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        return
    profile.invite_redeemed_at = datetime.now(UTC)
    profile.redeemed_invite_code = code
    await session.flush()


async def set_role(session: AsyncSession, user_id: UUID, role: str) -> UserProfile | None:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        return None
    profile.role = role
    await session.flush()
    return profile


async def delete_profile(session: AsyncSession, user_id: UUID) -> None:
    profile = await session.get(UserProfile, user_id)
    if profile is not None:
        await session.delete(profile)
        await session.flush()


async def list_profiles(
    session: AsyncSession, *, limit: int, offset: int, role: str | None = None
) -> list[UserProfile]:
    """Offset pagination, deliberately - the admin console's user list is
    browsed a page or two deep by a human, not scrolled by a feed. The
    "cursor pagination only" rule in CLAUDE.md is about feeds that grow under
    a reader mid-scroll; this table does not have that problem.

    There is no search-by-email: this table never stores one (only Supabase's
    auth.users does), so a user is identified here by id, role and invite
    status only.
    """
    query = select(UserProfile).order_by(UserProfile.created_at.desc()).limit(limit).offset(offset)
    if role:
        query = query.where(UserProfile.role == role)
    result = await session.execute(query)
    return list(result.scalars().all())
