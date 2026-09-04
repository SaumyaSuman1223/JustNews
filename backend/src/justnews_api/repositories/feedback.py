from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Feedback


async def create_feedback(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str | None,
    locale: str,
    path: str | None,
    message: str,
) -> Feedback:
    feedback = Feedback(
        user_id=user_id, session_id=session_id, locale=locale, path=path, message=message
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def list_feedback(session: AsyncSession, *, limit: int = 100) -> list[Feedback]:
    result = await session.execute(
        select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
