"""Reads for Discover's rail widgets. Written by the ingestion markets job."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import CompanyMention, MarketSnapshot


async def latest_snapshots(session: AsyncSession) -> list[MarketSnapshot]:
    """The newest snapshot of each symbol."""
    result = await session.execute(
        select(MarketSnapshot)
        .distinct(MarketSnapshot.symbol)
        .order_by(MarketSnapshot.symbol, MarketSnapshot.as_of.desc())
    )
    return list(result.scalars().all())


async def snapshot_series(
    session: AsyncSession, *, since: datetime
) -> list[tuple[str, datetime, float]]:
    """Every snapshot since ``since``, oldest first: (symbol, as_of, price)."""
    result = await session.execute(
        select(MarketSnapshot.symbol, MarketSnapshot.as_of, MarketSnapshot.price)
        .where(MarketSnapshot.as_of >= since)
        .order_by(MarketSnapshot.as_of)
    )
    return [(symbol, as_of, price) for symbol, as_of, price in result.all()]


async def company_mentions(session: AsyncSession) -> list[CompanyMention]:
    result = await session.execute(select(CompanyMention).order_by(CompanyMention.rank))
    return list(result.scalars().all())
