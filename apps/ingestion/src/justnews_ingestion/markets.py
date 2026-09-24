"""Discover's market widgets: quotes, and the companies in today's news.

Run by `justnews-ingest markets` on the ingest schedule. Writes
`market_snapshots` (the Market Outlook tiles and their sparklines) and
replaces `company_mentions` (Trending Companies). Nothing here runs in a
request path: the API serves these tables, cached (ADR 0014), so traffic can
never spend a provider's free quota.

Honest labels, not borrowed ones. Index futures and the VIX are not on any
reliable free tier, so the tiles are the ETFs that track them, and say so -
"S&P 500 · SPY", not "S&P Futures".
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, ArticleTopic, CompanyMention, MarketSnapshot, Topic
from justnews_core.settings import Settings

log = get_logger(__name__)

FINNHUB_QUOTE = "https://finnhub.io/api/v1/quote"
COINGECKO_PRICE = "https://api.coingecko.com/api/v3/simple/price"
TIMEOUT_SECONDS = 10.0
#: Two tries, a second apart: enough to ride out a blip, not enough to stall
#: the ingest run a provider outage is sharing a runner with.
ATTEMPTS = 2
#: Sparklines span a day; a little more than that is kept.
SNAPSHOT_RETENTION = timedelta(days=3)
MENTION_WINDOW = timedelta(hours=24)
TOP_COMPANIES = 6
#: A company named once is noise, not a trend.
MIN_MENTIONS = 2


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    label: str


#: The Market Outlook tiles, in order.
INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument("SPY", "S&P 500"),
    Instrument("QQQ", "Nasdaq 100"),
    Instrument("DIA", "Dow Jones"),
    Instrument("VIXY", "Volatility"),
)
BITCOIN = Instrument("BTC", "Bitcoin")


@dataclass(frozen=True, slots=True)
class Company:
    name: str
    ticker: str
    exchange: str
    domain: str
    #: Names a headline uses for it. Matched as whole words, case-sensitive,
    #: so "Apple" the company is not "apple" the fruit in a recipe headline.
    aliases: tuple[str, ...]
    #: Names that are also ordinary words or other things - "Shell", "BP"
    #: (blood pressure), "Amazon" (the river), "Intel" (intelligence). These
    #: count only in an article filed under business (BUSINESS_TOPIC), where
    #: the company is the likely reading. Case alone cannot settle them: a
    #: headline capitalises its first word, and some capitalise every word.
    ambiguous: tuple[str, ...] = ()


#: Curated by hand: big, frequently reported companies with their primary
#: listing. Quotes exist only for US listings on Finnhub's free tier; the
#: rest are still counted, and shown with their mentions and no price.
COMPANIES: tuple[Company, ...] = (
    Company("Apple", "AAPL", "NASDAQ", "apple.com", ("Apple Inc", "iPhone"), ("Apple",)),
    Company("Microsoft", "MSFT", "NASDAQ", "microsoft.com", ("Microsoft",)),
    Company("Alphabet", "GOOGL", "NASDAQ", "abc.xyz", ("Google", "Alphabet", "YouTube")),
    Company("Amazon", "AMZN", "NASDAQ", "amazon.com", ("Amazon.com", "AWS"), ("Amazon",)),
    Company(
        "Meta Platforms",
        "META",
        "NASDAQ",
        "meta.com",
        ("Facebook", "Instagram", "WhatsApp"),
        ("Meta",),
    ),
    Company("NVIDIA", "NVDA", "NASDAQ", "nvidia.com", ("Nvidia", "NVIDIA")),
    Company("Tesla", "TSLA", "NASDAQ", "tesla.com", ("Tesla",)),
    Company("Netflix", "NFLX", "NASDAQ", "netflix.com", ("Netflix",)),
    Company("Intel", "INTC", "NASDAQ", "intel.com", (), ("Intel",)),
    Company("AMD", "AMD", "NASDAQ", "amd.com", ("AMD",)),
    Company("Broadcom", "AVGO", "NASDAQ", "broadcom.com", ("Broadcom",)),
    Company("Oracle", "ORCL", "NYSE", "oracle.com", (), ("Oracle",)),
    Company("Salesforce", "CRM", "NYSE", "salesforce.com", ("Salesforce",)),
    Company("IBM", "IBM", "NYSE", "ibm.com", ("IBM",)),
    Company("Boeing", "BA", "NYSE", "boeing.com", ("Boeing",)),
    Company("Disney", "DIS", "NYSE", "disney.com", ("Disney",)),
    Company("JPMorgan Chase", "JPM", "NYSE", "jpmorganchase.com", ("JPMorgan", "JP Morgan")),
    Company("Goldman Sachs", "GS", "NYSE", "goldmansachs.com", ("Goldman Sachs",)),
    Company("Walmart", "WMT", "NYSE", "walmart.com", ("Walmart",)),
    Company("Exxon Mobil", "XOM", "NYSE", "exxonmobil.com", ("Exxon", "ExxonMobil")),
    Company("Chevron", "CVX", "NYSE", "chevron.com", ("Chevron",)),
    Company("Pfizer", "PFE", "NYSE", "pfizer.com", ("Pfizer",)),
    Company("Eli Lilly", "LLY", "NYSE", "lilly.com", ("Eli Lilly",)),
    Company(
        "Novo Nordisk", "NVO", "NYSE", "novonordisk.com", ("Novo Nordisk", "Ozempic", "Wegovy")
    ),
    Company("Uber", "UBER", "NYSE", "uber.com", ("Uber",)),
    Company("DoorDash", "DASH", "NASDAQ", "doordash.com", ("DoorDash",)),
    Company("Airbnb", "ABNB", "NASDAQ", "airbnb.com", ("Airbnb",)),
    Company("Palantir", "PLTR", "NASDAQ", "palantir.com", ("Palantir",)),
    Company("Coinbase", "COIN", "NASDAQ", "coinbase.com", ("Coinbase",)),
    Company("Spotify", "SPOT", "NYSE", "spotify.com", ("Spotify",)),
    Company("Toyota", "TM", "NYSE", "toyota.com", ("Toyota",)),
    Company("Sony", "SONY", "NYSE", "sony.com", ("Sony",)),
    Company("TSMC", "TSM", "NYSE", "tsmc.com", ("TSMC", "Taiwan Semiconductor")),
    Company("Samsung", "005930", "KRX", "samsung.com", ("Samsung",)),
    Company("Alibaba", "BABA", "NYSE", "alibaba.com", ("Alibaba",)),
    Company("Infosys", "INFY", "NYSE", "infosys.com", ("Infosys",)),
    Company("Wipro", "WIT", "NYSE", "wipro.com", ("Wipro",)),
    Company("HDFC Bank", "HDB", "NYSE", "hdfcbank.com", ("HDFC",)),
    Company("ICICI Bank", "IBN", "NYSE", "icicibank.com", ("ICICI",)),
    Company(
        "Reliance Industries",
        "RELIANCE",
        "NSE",
        "ril.com",
        ("Reliance Industries", "Reliance Jio", "Jio"),
        ("Reliance",),
    ),
    # The listed company, not the group: a Tata Steel or Tata Motors story is
    # not news about TCS, and a "Tata Group" row carried TCS's ticker.
    Company("Tata Consultancy Services", "TCS", "NSE", "tcs.com", ("TCS", "Tata Consultancy"), ()),
    Company(
        "Adani Enterprises", "ADANIENT", "NSE", "adani.com", ("Adani Enterprises",), ("Adani",)
    ),
    Company("Shell", "SHEL", "NYSE", "shell.com", (), ("Shell",)),
    Company("BP", "BP", "NYSE", "bp.com", (), ("BP",)),
    Company("HSBC", "HSBC", "NYSE", "hsbc.com", ("HSBC",)),
    Company("Nike", "NKE", "NYSE", "nike.com", ("Nike",)),
    Company("McDonald's", "MCD", "NYSE", "mcdonalds.com", ("McDonald's",)),
    Company("Starbucks", "SBUX", "NASDAQ", "starbucks.com", ("Starbucks",)),
    Company("Visa", "V", "NYSE", "visa.com", ("Visa Inc",), ("Visa",)),
)

QUOTED_EXCHANGES = frozenset({"NASDAQ", "NYSE"})


@dataclass(frozen=True, slots=True)
class Quote:
    price: float
    change: float
    change_pct: float


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, str]) -> object:
    """One GET with a timeout and a single retry on a network error or 5xx.
    A 4xx - a bad key, a rate limit - is not retried: asking again changes
    nothing."""
    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        try:
            response = await client.get(url, params=params, timeout=TIMEOUT_SECONDS)
            if response.status_code < 500:
                response.raise_for_status()
                return response.json()
            last = httpx.HTTPStatusError(
                f"HTTP {response.status_code}", request=response.request, response=response
            )
        except httpx.HTTPStatusError:
            raise
        except (httpx.TransportError, ValueError) as exc:
            last = exc
        if attempt + 1 < ATTEMPTS:
            await asyncio.sleep(1.0)
    assert last is not None
    raise last


async def finnhub_quote(client: httpx.AsyncClient, settings: Settings, symbol: str) -> Quote | None:
    """Finnhub's quote, or None when it has none - an unknown symbol comes
    back as all zeros rather than as an error."""
    if not settings.finnhub_api_key:
        return None
    data = await _get_json(
        client, FINNHUB_QUOTE, {"symbol": symbol, "token": settings.finnhub_api_key}
    )
    if not isinstance(data, dict):
        return None
    price, change, pct = data.get("c"), data.get("d"), data.get("dp")
    if not isinstance(price, int | float) or price <= 0:
        return None
    return Quote(
        price=float(price),
        change=float(change) if isinstance(change, int | float) else 0.0,
        change_pct=float(pct) if isinstance(pct, int | float) else 0.0,
    )


async def bitcoin_quote(client: httpx.AsyncClient) -> Quote | None:
    data = await _get_json(
        client,
        COINGECKO_PRICE,
        {"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
    )
    entry = data.get("bitcoin") if isinstance(data, dict) else None
    if not isinstance(entry, dict):
        return None
    price, pct = entry.get("usd"), entry.get("usd_24h_change")
    if not isinstance(price, int | float) or not isinstance(pct, int | float):
        return None
    # CoinGecko gives the 24h change as a percentage only; the absolute move
    # is the difference from the price that percentage started at.
    change = float(price) - float(price) / (1 + float(pct) / 100)
    return Quote(price=float(price), change=change, change_pct=float(pct))


async def refresh_markets(
    session: AsyncSession, settings: Settings, client: httpx.AsyncClient, *, now: datetime
) -> int:
    """Record one snapshot per instrument; returns how many were recorded.
    A provider that fails is logged and skipped - the others still land."""
    rows: list[MarketSnapshot] = []
    if not settings.finnhub_api_key:
        log.warning("markets_no_finnhub_key", skipped=[i.symbol for i in INSTRUMENTS])
    for instrument in INSTRUMENTS:
        try:
            quote = await finnhub_quote(client, settings, instrument.symbol)
        except httpx.HTTPError as exc:
            log.warning("markets_quote_failed", symbol=instrument.symbol, error=str(exc))
            continue
        if quote is not None:
            rows.append(_snapshot(instrument, quote, provider="finnhub", now=now))
    try:
        btc = await bitcoin_quote(client)
    except httpx.HTTPError as exc:
        log.warning("markets_quote_failed", symbol=BITCOIN.symbol, error=str(exc))
        btc = None
    if btc is not None:
        rows.append(_snapshot(BITCOIN, btc, provider="coingecko", now=now))

    session.add_all(rows)
    await session.execute(
        delete(MarketSnapshot).where(MarketSnapshot.as_of < now - SNAPSHOT_RETENTION)
    )
    return len(rows)


def _snapshot(
    instrument: Instrument, quote: Quote, *, provider: str, now: datetime
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=instrument.symbol,
        label=instrument.label,
        price=quote.price,
        change=quote.change,
        change_pct=quote.change_pct,
        currency="USD",
        provider=provider,
        as_of=now,
    )


#: IPTC "economy, business and finance": an article under it, or under any
#: of its descendants, is a business story for ``Company.ambiguous``.
BUSINESS_TOPIC = "medtop:04000000"


def _pattern(names: tuple[str, ...]) -> re.Pattern[str] | None:
    if not names:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(n) for n in names) + r")(?![\w])")


def _patterns() -> list[tuple[Company, re.Pattern[str] | None, re.Pattern[str] | None]]:
    return [
        (company, _pattern(company.aliases), _pattern(company.ambiguous)) for company in COMPANIES
    ]


def count_mentions(texts: list[tuple[str, bool]]) -> Counter[Company]:
    """How many of these articles name each company - one per article, however
    many times it repeats the name, so a single long piece is not a trend.

    Each text comes with whether its article is a business story, which is
    what lets an ambiguous name count."""
    counts: Counter[Company] = Counter()
    patterns = _patterns()
    for text, business in texts:
        for company, plain, ambiguous in patterns:
            if (plain and plain.search(text)) or (
                business and ambiguous and ambiguous.search(text)
            ):
                counts[company] += 1
    return counts


async def refresh_companies(
    session: AsyncSession, settings: Settings, client: httpx.AsyncClient, *, now: datetime
) -> int:
    """Replace Trending Companies with the most-named companies of the last
    day's live articles. Returns how many were written."""
    business = (
        select(ArticleTopic.article_id)
        .join(Topic, Topic.id == ArticleTopic.topic_id)
        .where(ArticleTopic.article_id == Article.id, Topic.path.contains([BUSINESS_TOPIC]))
        .exists()
    )
    result = await session.execute(
        select(Article.title, Article.snippet, business).where(
            Article.fetched_at >= now - MENTION_WINDOW, Article.removed_at.is_(None)
        )
    )
    texts = [
        (f"{title} {snippet or ''}", is_business) for title, snippet, is_business in result.all()
    ]
    ranked = [
        (company, count)
        for company, count in count_mentions(texts).most_common()
        if count >= MIN_MENTIONS
    ][:TOP_COMPANIES]

    rows: list[CompanyMention] = []
    for rank, (company, count) in enumerate(ranked, start=1):
        quote: Quote | None = None
        if company.exchange in QUOTED_EXCHANGES:
            try:
                quote = await finnhub_quote(client, settings, company.ticker)
            except httpx.HTTPError as exc:
                log.warning("companies_quote_failed", ticker=company.ticker, error=str(exc))
        rows.append(
            CompanyMention(
                rank=rank,
                name=company.name,
                ticker=company.ticker,
                exchange=company.exchange,
                domain=company.domain,
                mentions=count,
                price=quote.price if quote else None,
                change_pct=quote.change_pct if quote else None,
                as_of=now,
            )
        )

    await session.execute(delete(CompanyMention))
    session.add_all(rows)
    return len(rows)


async def refresh(session: AsyncSession, settings: Settings) -> dict[str, int]:
    now = datetime.now(UTC)
    async with httpx.AsyncClient(headers={"User-Agent": settings.ingest_user_agent}) as client:
        quotes = await refresh_markets(session, settings, client, now=now)
        companies = await refresh_companies(session, settings, client, now=now)
    await session.commit()
    log.info("markets_refreshed", quotes=quotes, companies=companies)
    return {"quotes": quotes, "companies": companies}
