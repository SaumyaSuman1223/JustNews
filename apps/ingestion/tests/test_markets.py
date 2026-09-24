"""The markets job: quotes into snapshots, and the companies in the news."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, CompanyMention, MarketSnapshot, Topic
from justnews_core.settings import Settings
from justnews_ingestion import markets

NOW = datetime(2026, 9, 23, 15, 0, tzinfo=UTC)
KEYED = Settings(finnhub_api_key="test-key")  # type: ignore[call-arg]


def _client(*, finnhub_status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "finnhub.io":
            if finnhub_status != 200:
                return httpx.Response(finnhub_status)
            symbol = request.url.params["symbol"]
            if symbol == "VIXY":
                # Finnhub's answer for a symbol it has no quote for.
                return httpx.Response(200, json={"c": 0, "d": None, "dp": None})
            return httpx.Response(200, json={"c": 500.0, "d": 5.0, "dp": 1.01})
        if request.url.host == "api.coingecko.com":
            return httpx.Response(200, json={"bitcoin": {"usd": 110000.0, "usd_24h_change": 10.0}})
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestCountMentions:
    def test_counts_each_article_once(self) -> None:
        counts = markets.count_mentions(
            [("Tesla, Tesla, Tesla everywhere", False), ("Tesla recalls cars", False)]
        )
        tesla = next(c for c in markets.COMPANIES if c.ticker == "TSLA")
        assert counts[tesla] == 2

    def test_matches_whole_words_and_case(self) -> None:
        # "apple" the fruit and "Metaverse" are not Apple and Meta.
        counts = markets.count_mentions([("An apple a day", True), ("The Metaverse is back", True)])
        assert counts == {}

    def test_an_alias_counts_for_its_company(self) -> None:
        counts = markets.count_mentions([("WhatsApp outage hits millions", False)])
        assert {c.ticker for c in counts} == {"META"}

    def test_an_ambiguous_name_counts_only_in_a_business_story(self) -> None:
        # Shell shock, high BP, the Amazon basin, US intel: not the companies.
        outside = markets.count_mentions(
            [
                ("Shell shock after the vote", False),
                ("High BP in young adults", False),
                ("Fires spread across the Amazon", False),
                ("Intel suggests a second attack", False),
            ]
        )
        assert outside == {}
        inside = markets.count_mentions([("Shell and BP raise dividends", True)])
        assert {c.ticker for c in inside} == {"SHEL", "BP"}

    def test_an_unambiguous_alias_needs_no_business_context(self) -> None:
        counts = markets.count_mentions([("New iPhone goes on sale", False)])
        assert {c.ticker for c in counts} == {"AAPL"}


class TestRefreshMarkets:
    async def test_records_each_quote_and_skips_ones_without_a_price(
        self, session: AsyncSession
    ) -> None:
        async with _client() as client:
            recorded = await markets.refresh_markets(session, KEYED, client, now=NOW)
        await session.commit()

        rows = (await session.execute(select(MarketSnapshot))).scalars().all()
        assert recorded == len(rows) == 4
        assert {row.symbol for row in rows} == {"SPY", "QQQ", "DIA", "BTC"}
        btc = next(row for row in rows if row.symbol == "BTC")
        assert btc.provider == "coingecko"
        # 10% up to 110,000 means it started at 100,000.
        assert round(btc.change) == 10000

    async def test_without_a_key_only_bitcoin_is_recorded(self, session: AsyncSession) -> None:
        async with _client() as client:
            recorded = await markets.refresh_markets(
                session,
                Settings(),  # type: ignore[call-arg]
                client,
                now=NOW,
            )
        assert recorded == 1

    async def test_a_failing_provider_does_not_stop_the_others(self, session: AsyncSession) -> None:
        async with _client(finnhub_status=429) as client:
            recorded = await markets.refresh_markets(session, KEYED, client, now=NOW)
        assert recorded == 1  # Bitcoin still lands.

    async def test_prunes_old_snapshots(self, session: AsyncSession) -> None:
        session.add(
            markets._snapshot(
                markets.BITCOIN,
                markets.Quote(price=1.0, change=0.0, change_pct=0.0),
                provider="coingecko",
                now=NOW - timedelta(days=4),
            )
        )
        await session.commit()
        async with _client() as client:
            await markets.refresh_markets(session, KEYED, client, now=NOW)
        await session.commit()
        old = await session.execute(
            select(MarketSnapshot).where(MarketSnapshot.as_of < NOW - timedelta(days=3))
        )
        assert old.scalars().all() == []


class TestRefreshCompanies:
    async def test_ranks_the_most_named_and_replaces_the_last_run(
        self, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        business = await session.get(Topic, markets.BUSINESS_TOPIC) or await make_topic(
            session, markets.BUSINESS_TOPIC, slug="economy-business-finance"
        )
        for index in range(3):
            await make_article(session, source, title=f"Tesla story {index}")
        for index in range(2):
            article = await make_article(session, source, title=f"Reliance profit {index}")
            session.add(ArticleTopic(article_id=article.id, topic_id=business.id))
        # Not filed under business, so "Shell" is not the company here.
        for index in range(2):
            await make_article(session, source, title=f"Shell shock {index}")
        await make_article(session, source, title="Boeing once")
        session.add(
            CompanyMention(
                rank=1,
                name="Stale",
                ticker="OLD",
                exchange="NYSE",
                domain="old.example",
                mentions=9,
                as_of=NOW - timedelta(hours=1),
            )
        )
        await session.commit()

        async with _client() as client:
            written = await markets.refresh_companies(session, KEYED, client, now=datetime.now(UTC))
        await session.commit()

        rows = (
            (await session.execute(select(CompanyMention).order_by(CompanyMention.rank)))
            .scalars()
            .all()
        )
        assert written == 2
        assert [(row.ticker, row.mentions) for row in rows] == [("TSLA", 3), ("RELIANCE", 2)]
        # A US listing gets its quote; an NSE one is counted with no price.
        assert rows[0].price == 500.0
        assert rows[1].price is None
