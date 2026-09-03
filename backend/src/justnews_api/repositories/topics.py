from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Topic


async def list_top_level_topics(session: AsyncSession) -> list[Topic]:
    result = await session.execute(
        select(Topic).where(Topic.active.is_(True), Topic.level == 1).order_by(Topic.id)
    )
    # Topic.labels is lazy="selectin", so this is one query, not N+1.
    return list(result.scalars().unique().all())
