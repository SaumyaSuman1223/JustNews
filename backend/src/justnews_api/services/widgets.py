"""Discover's rail widgets: Market Outlook and Trending Companies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import widgets as repo
from justnews_core.models import CompanyMention

#: A tile's sparkline covers the last day of snapshots.
SERIES_WINDOW = timedelta(hours=24)
#: Tiles in this order; anything else the job recorded is left off.
TILE_ORDER = ("SPY", "QQQ", "BTC", "VIXY", "DIA")
MAX_TILES = 4
#: A quote older than this is not "the market now" - it is shown as stale by
#: its own timestamp, but a tile whose job stopped days ago is dropped.
MAX_QUOTE_AGE = timedelta(days=4)


@dataclass(frozen=True, slots=True)
class MarketTile:
    symbol: str
    label: str
    price: float
    change: float
    change_pct: float
    currency: str
    as_of: datetime
    series: list[float]


async def market_outlook(session: AsyncSession, *, now: datetime | None = None) -> list[MarketTile]:
    now = now or datetime.now(UTC)
    latest = {
        row.symbol: row
        for row in await repo.latest_snapshots(session)
        if now - row.as_of <= MAX_QUOTE_AGE
    }
    series: dict[str, list[float]] = {}
    for symbol, _, price in await repo.snapshot_series(session, since=now - SERIES_WINDOW):
        series.setdefault(symbol, []).append(price)
    tiles = [
        MarketTile(
            symbol=row.symbol,
            label=row.label,
            price=row.price,
            change=row.change,
            change_pct=row.change_pct,
            currency=row.currency,
            as_of=row.as_of,
            series=series.get(row.symbol, [row.price]),
        )
        for symbol in TILE_ORDER
        if (row := latest.get(symbol)) is not None
    ]
    return tiles[:MAX_TILES]


async def trending_companies(session: AsyncSession) -> list[CompanyMention]:
    return await repo.company_mentions(session)
