from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core import cache
from justnews_api.core.db import get_session
from justnews_api.services import widgets as service

router = APIRouter(prefix="/v1/widgets", tags=["widgets"])


class MarketTileOut(BaseModel):
    symbol: str
    label: str = Field(description="What the instrument tracks, e.g. 'S&P 500' for SPY.")
    price: float
    change: float
    change_pct: float
    currency: str
    as_of: datetime
    series: list[float] = Field(description="The last day's prices, oldest first.")


class CompanyOut(BaseModel):
    rank: int
    name: str
    ticker: str
    exchange: str
    domain: str
    mentions: int = Field(description="Articles in the last day that name the company.")
    price: float | None = Field(description="Null where the free quote source has no listing.")
    change_pct: float | None
    as_of: datetime


@router.get("/markets", response_model=list[MarketTileOut])
async def markets(session: AsyncSession = Depends(get_session)) -> list[MarketTileOut]:
    """Market Outlook. Cache: 120s fresh + 600s stale (ADR 0014) - the job
    that writes these runs every fifteen minutes."""

    async def load(s: AsyncSession) -> list[dict[str, Any]]:
        return [
            MarketTileOut(
                symbol=tile.symbol,
                label=tile.label,
                price=tile.price,
                change=tile.change,
                change_pct=tile.change_pct,
                currency=tile.currency,
                as_of=tile.as_of,
                series=tile.series,
            ).model_dump(mode="json")
            for tile in await service.market_outlook(s)
        ]

    payload = await cache.read_through(
        "widgets:markets", ttl=120, stale=600, session=session, load=load
    )
    return [MarketTileOut.model_validate(item) for item in payload]


@router.get("/companies", response_model=list[CompanyOut])
async def companies(session: AsyncSession = Depends(get_session)) -> list[CompanyOut]:
    """Trending Companies. Cache: 300s fresh + 1800s stale (ADR 0014)."""

    async def load(s: AsyncSession) -> list[dict[str, Any]]:
        return [
            CompanyOut(
                rank=row.rank,
                name=row.name,
                ticker=row.ticker,
                exchange=row.exchange,
                domain=row.domain,
                mentions=row.mentions,
                price=row.price,
                change_pct=row.change_pct,
                as_of=row.as_of,
            ).model_dump(mode="json")
            for row in await service.trending_companies(s)
        ]

    payload = await cache.read_through(
        "widgets:companies", ttl=300, stale=1800, session=session, load=load
    )
    return [CompanyOut.model_validate(item) for item in payload]
