from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import FeatureFlag


async def get_flag(session: AsyncSession, key: str) -> FeatureFlag | None:
    return await session.get(FeatureFlag, key)


async def is_enabled(session: AsyncSession, key: str, *, default: bool = True) -> bool:
    """A key with no row reads as `default` - a flag not yet created must not
    be able to silently disable the thing it would gate, which is what makes
    it safe to check a flag before the corresponding admin migration/seed row
    has landed anywhere a session might read from."""
    flag = await get_flag(session, key)
    return flag.enabled if flag is not None else default


async def list_flags(session: AsyncSession) -> list[FeatureFlag]:
    result = await session.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return list(result.scalars().all())


async def set_enabled(
    session: AsyncSession, key: str, *, enabled: bool, admin_user_id: UUID
) -> FeatureFlag | None:
    flag = await get_flag(session, key)
    if flag is None:
        return None
    flag.enabled = enabled
    flag.updated_by = admin_user_id
    flag.updated_at = datetime.now(UTC)
    await session.flush()
    return flag


async def create_flag(
    session: AsyncSession, *, key: str, description: str, enabled: bool, admin_user_id: UUID
) -> FeatureFlag:
    flag = FeatureFlag(key=key, enabled=enabled, description=description, updated_by=admin_user_id)
    session.add(flag)
    await session.flush()
    return flag
