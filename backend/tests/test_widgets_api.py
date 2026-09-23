"""Integration tests for Discover's rail widgets."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import CompanyMention, MarketSnapshot


def _snapshot(symbol: str, label: str, price: float, minutes_ago: int) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        label=label,
        price=price,
        change=1.0,
        change_pct=0.5,
        currency="USD",
        provider="finnhub",
        as_of=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )


class TestMarkets:
    async def test_latest_quote_per_symbol_with_its_day_as_a_series(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        session.add_all(
            [
                _snapshot("SPY", "S&P 500", 500.0, 60),
                _snapshot("SPY", "S&P 500", 502.0, 30),
                _snapshot("SPY", "S&P 500", 503.5, 0),
                _snapshot("BTC", "Bitcoin", 110000.0, 0),
                # Older than a day: not in the sparkline.
                _snapshot("BTC", "Bitcoin", 90000.0, 60 * 30),
            ]
        )
        await session.commit()

        body = (await client.get("/v1/widgets/markets")).json()
        assert [tile["symbol"] for tile in body] == ["SPY", "BTC"]
        assert body[0]["price"] == 503.5
        assert body[0]["series"] == [500.0, 502.0, 503.5]
        assert body[1]["series"] == [110000.0]

    async def test_a_quote_days_old_is_not_shown(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        session.add(_snapshot("SPY", "S&P 500", 500.0, 60 * 24 * 5))
        await session.commit()
        assert (await client.get("/v1/widgets/markets")).json() == []


class TestCompanies:
    async def test_in_rank_order(self, client: AsyncClient, session: AsyncSession) -> None:
        now = datetime.now(UTC)
        session.add_all(
            [
                CompanyMention(
                    rank=2,
                    name="Reliance Industries",
                    ticker="RELIANCE",
                    exchange="NSE",
                    domain="ril.com",
                    mentions=4,
                    price=None,
                    change_pct=None,
                    as_of=now,
                ),
                CompanyMention(
                    rank=1,
                    name="Tesla",
                    ticker="TSLA",
                    exchange="NASDAQ",
                    domain="tesla.com",
                    mentions=9,
                    price=250.0,
                    change_pct=-1.2,
                    as_of=now,
                ),
            ]
        )
        await session.commit()

        body = (await client.get("/v1/widgets/companies")).json()
        assert [(c["ticker"], c["mentions"], c["price"]) for c in body] == [
            ("TSLA", 9, 250.0),
            ("RELIANCE", 4, None),
        ]
