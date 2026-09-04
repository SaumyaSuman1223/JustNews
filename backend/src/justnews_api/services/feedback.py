from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import feedback as repo
from justnews_core.errors import ValidationError
from justnews_core.models import Feedback

MAX_MESSAGE_LENGTH = 2000


async def submit_feedback(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    session_id: str | None,
    locale: str,
    path: str | None,
    message: str,
) -> Feedback:
    message = message.strip()
    if not message or len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"message must be 1 to {MAX_MESSAGE_LENGTH} characters.")
    return await repo.create_feedback(
        session, user_id=user_id, session_id=session_id, locale=locale, path=path, message=message
    )


async def list_feedback(session: AsyncSession, *, limit: int = 100) -> list[Feedback]:
    return await repo.list_feedback(session, limit=limit)
