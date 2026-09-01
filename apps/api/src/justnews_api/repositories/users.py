from __future__ import annotations

from uuid import UUID

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
