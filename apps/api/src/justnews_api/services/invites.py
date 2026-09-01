from __future__ import annotations

import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import admin as admin_repo
from justnews_api.repositories import invites as repo
from justnews_api.repositories import users as users_repo
from justnews_core.errors import ConflictError, NotFoundError, ValidationError
from justnews_core.models import InviteCode


async def redeem_for_user(session: AsyncSession, user_id: UUID, code: str) -> None:
    code = code.strip()
    if not code:
        raise ValidationError("An invite code is required.")

    profile = await users_repo.get_profile(session, user_id)
    if profile is not None and profile.invite_redeemed_at is not None:
        raise ConflictError("This account has already redeemed an invite.")

    invite = await repo.get_invite(session, code)
    if invite is None:
        raise NotFoundError("That invite code is not valid.")

    if not await repo.redeem(session, code):
        raise ConflictError("That invite code has expired or has no uses left.")

    await users_repo.mark_invite_redeemed(session, user_id, code)


def generate_code() -> str:
    # 16 base32 chars ~ 80 bits - not guessable, and short enough to read
    # aloud or type from an invite email.
    return secrets.token_hex(8)


async def create_invite(
    session: AsyncSession,
    *,
    admin_user_id: UUID,
    note: str | None,
    max_uses: int,
    expires_at: datetime | None,
) -> InviteCode:
    if not 1 <= max_uses <= 10_000:
        raise ValidationError("max_uses must be between 1 and 10000.")
    invite = await repo.create_invite(
        session,
        code=generate_code(),
        note=note,
        max_uses=max_uses,
        expires_at=expires_at,
        created_by=admin_user_id,
    )
    await admin_repo.record_action(
        session,
        admin_user_id=admin_user_id,
        action="invite.create",
        target_type="invite_code",
        target_id=invite.code,
        details={"max_uses": max_uses, "note": note},
    )
    return invite


async def list_invites(session: AsyncSession) -> list[InviteCode]:
    return await repo.list_invites(session)
