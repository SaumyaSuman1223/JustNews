from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.auth import require_user
from justnews_api.core.db import get_user_session
from justnews_api.services import invites as service
from justnews_api.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["invites"])


class RedeemIn(BaseModel):
    code: str


@router.post("/invites/redeem", status_code=status.HTTP_204_NO_CONTENT)
async def redeem_invite(
    body: RedeemIn,
    principal: Principal = Depends(require_user),
    # get_user_session, not get_beta_session - redeeming a code is how a
    # reader gets beta access in the first place.
    session: AsyncSession = Depends(get_user_session),
) -> None:
    await service.redeem_for_user(session, principal.user_id, body.code)
