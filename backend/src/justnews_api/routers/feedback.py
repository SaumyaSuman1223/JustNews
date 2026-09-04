from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_beta_session
from justnews_api.services import feedback as service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["feedback"])


class FeedbackIn(BaseModel):
    message: str
    locale: str
    path: str | None = None


class FeedbackOut(BaseModel):
    id: int
    created_at: datetime


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackIn,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_beta_session),
    x_session_id: str | None = Header(default=None, alias="x-session-id"),
) -> FeedbackOut:
    feedback = await service.submit_feedback(
        session,
        user_id=principal.user_id,
        session_id=x_session_id,
        locale=body.locale,
        path=body.path,
        message=body.message,
    )
    return FeedbackOut(id=feedback.id, created_at=feedback.created_at)
