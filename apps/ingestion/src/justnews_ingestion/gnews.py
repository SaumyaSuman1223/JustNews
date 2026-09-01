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
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.errors import QuotaExceededError, UpstreamError
from justnews_core.language import LAUNCH_LANGUAGES, detect_language
from justnews_core.logging import get_logger
from justnews_core.models import ApiQuotaUsage, Article
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


def _parse_articles(payload: Any, *, language: str, settings: Settings) -> list[ParsedEntry]:
    now = datetime.now(UTC)
    entries: list[ParsedEntry] = []
    raw_articles = payload.get("articles") if isinstance(payload, dict) else None
    for item in raw_articles if isinstance(raw_articles, list) else []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = normalise_text(item.get("title") or "")
        if not url or not title:
            continue
        try:
            url_canonical = canonicalise_url(str(url))
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

        source = item.get("source")
        source = source if isinstance(source, dict) else {}

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
                source_name=source.get("name") or None,
                source_url=source.get("url") or None,
            )
        )
    return entries


async def _call(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    path: str,
    params: dict[str, str],
    language: str,
) -> list[ParsedEntry]:
    if not settings.gnews_api_key:
        raise UpstreamError(PROVIDER, "GNEWS_API_KEY is not configured.")

    await reserve_call(session, settings)

    try:
        response = await client.get(
            f"{GNEWS_ENDPOINT}/{path}", params=params | {"apikey": settings.gnews_api_key}
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise UpstreamError(PROVIDER, f"HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError(PROVIDER, f"{type(exc).__name__}: {exc}") from exc
    except ValueError as exc:
        raise UpstreamError(PROVIDER, "Response was not valid JSON.") from exc

    return _parse_articles(payload, language=language, settings=settings)


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
    """One GNews keyword search. Costs exactly one call from the daily budget."""
    params = {"q": query, "lang": language, "max": str(min(max_results, 10))}
    if country:
        params["country"] = country

    entries = await _call(
        session, client, settings, path="search", params=params, language=language
    )
    log.info("gnews_search", query=query, language=language, returned=len(entries))
    return entries


async def top_headlines(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    language: str,
    category: str = "general",
    max_results: int = 10,
) -> list[ParsedEntry]:
    """One GNews top-headlines call - general backfill, no keyword needed.

    This is what `run` uses for thin-language backfill: there is no natural
    search query for "this language doesn't have much coverage yet," but
    top-headlines doesn't need one.
    """
    params = {"lang": language, "category": category, "max": str(min(max_results, 10))}
    entries = await _call(
        session, client, settings, path="top-headlines", params=params, language=language
    )
    log.info("gnews_top_headlines", language=language, category=category, returned=len(entries))
    return entries


async def thin_languages(session: AsyncSession, *, since: datetime, limit: int) -> list[str]:
    """The launch languages with the fewest articles published since ``since``.

    A language absent from the corpus entirely counts as zero and ranks
    first - `run`'s GNews backfill exists precisely for that case. Ties break
    on LAUNCH_LANGUAGES' own order, so the result is deterministic.
    """
    result = await session.execute(
        select(Article.language, func.count())
        .where(Article.published_at >= since, Article.language.in_(LAUNCH_LANGUAGES))
        .group_by(Article.language)
    )
    counts: dict[str, int] = dict(result.tuples().all())
    ranked = sorted(
        LAUNCH_LANGUAGES, key=lambda lang: (counts.get(lang, 0), LAUNCH_LANGUAGES.index(lang))
    )
    return ranked[:limit]
