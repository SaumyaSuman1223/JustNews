"""GNews client, budget-enforced.

GNews' free tier is 100 requests a day, 10 articles each, behind a 12-hour
delay, and the counter resets at 00:00 UTC. That delay is why GNews cannot be
the primary source (ADR 0003): it backfills topics and languages where our RSS
coverage is thin, which for a global corpus is the non-English long tail.

The budget is enforced *before* a call is made, in the database, so two
concurrent jobs cannot both believe they have quota left.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.errors import QuotaExceededError, UpstreamError
from justnews_core.language import detect_language
from justnews_core.logging import get_logger
from justnews_core.models import ApiQuotaUsage
from justnews_core.settings import Settings
from justnews_core.text import canonicalise_url, make_snippet, normalise_text
from justnews_ingestion.rss import ParsedEntry

log = get_logger(__name__)

GNEWS_ENDPOINT = "https://gnews.io/api/v4"
PROVIDER = "gnews"


@dataclass(frozen=True, slots=True)
class QuotaState:
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


def _today() -> datetime:
    return datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)


async def get_quota(session: AsyncSession, settings: Settings) -> QuotaState:
    used = await session.scalar(
        select(ApiQuotaUsage.calls).where(
            ApiQuotaUsage.provider == PROVIDER, ApiQuotaUsage.usage_date == _today()
        )
    )
    return QuotaState(used=used or 0, limit=settings.ingest_max_gnews_calls_per_day)


async def reserve_call(session: AsyncSession, settings: Settings) -> None:
    """Claim one call against today's budget, or refuse.

    The upsert is atomic and the check reads back the incremented value, so two
    workers racing on the last available call cannot both win.
    """
    statement = (
        insert(ApiQuotaUsage)
        .values(provider=PROVIDER, usage_date=_today(), calls=1)
        .on_conflict_do_update(
            index_elements=[ApiQuotaUsage.provider, ApiQuotaUsage.usage_date],
            set_={"calls": ApiQuotaUsage.calls + 1},
        )
        .returning(ApiQuotaUsage.calls)
    )
    calls = await session.scalar(statement)
    if calls is not None and calls > settings.ingest_max_gnews_calls_per_day:
        raise QuotaExceededError(
            f"GNews daily budget of {settings.ingest_max_gnews_calls_per_day} calls is spent."
        )


async def search(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    query: str,
    language: str,
    country: str | None = None,
    max_results: int = 10,
) -> list[ParsedEntry]:
    """One GNews search. Costs exactly one call from the daily budget."""
    if not settings.gnews_api_key:
        raise UpstreamError(PROVIDER, "GNEWS_API_KEY is not configured.")

    await reserve_call(session, settings)

    params = {
        "q": query,
        "lang": language,
        "max": str(min(max_results, 10)),
        "apikey": settings.gnews_api_key,
    }
    if country:
        params["country"] = country

    try:
        response = await client.get(f"{GNEWS_ENDPOINT}/search", params=params)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise UpstreamError(PROVIDER, f"HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError(PROVIDER, f"{type(exc).__name__}: {exc}") from exc
    except ValueError as exc:
        raise UpstreamError(PROVIDER, "Response was not valid JSON.") from exc

    now = datetime.now(UTC)
    entries: list[ParsedEntry] = []
    for item in payload.get("articles", []):
        url = item.get("url")
        title = normalise_text(item.get("title") or "")
        if not url or not title:
            continue
        try:
            url_canonical = canonicalise_url(url)
        except ValueError:
            continue

        snippet = make_snippet(item.get("description"), settings.ingest_snippet_max_chars)
        published_raw = item.get("publishedAt")
        try:
            published_at = (
                datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
                if published_raw
                else now
            )
        except ValueError:
            published_at = now

        entries.append(
            ParsedEntry(
                url_canonical=url_canonical,
                title=title,
                snippet=snippet,
                image_url=item.get("image"),
                author_name=None,
                language=detect_language(f"{title} {snippet or ''}", fallback=language),
                published_at=min(published_at.astimezone(UTC), now),
                raw_categories=[],
            )
        )

    log.info("gnews_search", query=query, language=language, returned=len(entries))
    return entries
