from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import InviteCode


async def get_invite(session: AsyncSession, code: str) -> InviteCode | None:
    return await session.get(InviteCode, code)


async def redeem(session: AsyncSession, code: str) -> bool:
    """Atomically claims one use of a code.

    The ``uses < max_uses`` guard lives in the UPDATE's own WHERE clause, not
    in a read-then-write in Python - two readers racing on the same code
    would otherwise both pass a prior read and both succeed, oversubscribing
    it. Only one UPDATE can match a given row at a time; the loser sees
    ``rowcount == 0``.
    """
    result = await session.execute(
        update(InviteCode)
        .where(
            InviteCode.code == code,
            InviteCode.uses < InviteCode.max_uses,
            (InviteCode.expires_at.is_(None)) | (InviteCode.expires_at > datetime.now(UTC)),
        )
        .values(uses=InviteCode.uses + 1)
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def create_invite(
    session: AsyncSession,
    *,
    code: str,
    note: str | None,
    max_uses: int,
    expires_at: datetime | None,
    created_by: UUID,
) -> InviteCode:
    invite = InviteCode(
        code=code, note=note, max_uses=max_uses, expires_at=expires_at, created_by=created_by
    )
    session.add(invite)
    await session.flush()
    return invite


async def list_invites(session: AsyncSession) -> list[InviteCode]:
    result = await session.execute(select(InviteCode).order_by(InviteCode.created_at.desc()))
    return list(result.scalars().all())
