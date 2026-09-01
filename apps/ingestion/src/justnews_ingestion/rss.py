"""RSS and Atom fetching.

RSS is the primary source: near-real-time, unlimited and free, where GNews'
free tier is 100 calls a day behind a 12-hour delay (ADR 0003).

Two mechanisms carry the weight here. Conditional GETs (``ETag`` /
``If-Modified-Since``) mean a 15-minute poll over hundreds of feeds mostly
returns 304 and costs nobody anything. Per-feed exponential backoff means one
dead feed cannot slow or fail a run.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from justnews_core.language import detect_language, normalise_language_code
from justnews_core.logging import get_logger
from justnews_core.models import Feed
from justnews_core.settings import Settings
from justnews_core.text import canonicalise_url, make_snippet, normalise_text
from justnews_ingestion.http import PoliteClient

log = get_logger(__name__)

BACKOFF_BASE_MINUTES = 15
BACKOFF_MAX_MINUTES = 6 * 60


@dataclass(slots=True)
class ParsedEntry:
    url_canonical: str
    title: str
    snippet: str | None
    image_url: str | None
    author_name: str | None
    language: str
    published_at: datetime
    raw_categories: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FeedResult:
    feed_id: int
    status: str  # ok | not_modified | failed | skipped
    entries: list[ParsedEntry] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None


def backoff_until(consecutive_failures: int, *, now: datetime) -> datetime:
    """Exponential backoff, capped. A feed that has failed nine times in a row
    is checked every six hours, not every fifteen minutes."""
    if consecutive_failures <= 0:
        return now
    minutes = min(BACKOFF_BASE_MINUTES * (2 ** (consecutive_failures - 1)), BACKOFF_MAX_MINUTES)
    return now + timedelta(minutes=minutes)


def is_due(feed: Feed, *, now: datetime) -> bool:
    if not feed.active:
        return False
    if feed.last_fetched_at is None:
        return True
    return now >= backoff_until(feed.consecutive_failures, now=feed.last_fetched_at)


def _entry_published(entry: object, *, now: datetime) -> datetime:
    """Publication time, clamped to the present.

    Feeds routinely emit timestamps hours in the future - misconfigured
    timezones, mostly. Left alone those articles pin themselves to the top of
    a recency-ordered feed forever.
    """
    for attribute in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attribute, None) or (
            entry.get(attribute) if isinstance(entry, dict) else None
        )
        if parsed:
            try:
                year, month, day, hour, minute, second = (int(part) for part in parsed[:6])
                candidate = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
            except (TypeError, ValueError):
                continue
            return min(candidate, now)

    for attribute in ("published", "updated"):
        raw = entry.get(attribute) if isinstance(entry, dict) else getattr(entry, attribute, None)
        if raw:
            try:
                candidate = parsedate_to_datetime(str(raw))
            except (TypeError, ValueError):
                continue
            if candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=UTC)
            return min(candidate.astimezone(UTC), now)

    return now


def _entry_image(entry: object) -> str | None:
    for link in getattr(entry, "links", []) or []:
        if str(link.get("type", "")).startswith("image/") and link.get("href"):
            return str(link["href"])
    for media in getattr(entry, "media_content", []) or []:
        if media.get("url"):
            return str(media["url"])
    for thumbnail in getattr(entry, "media_thumbnail", []) or []:
        if thumbnail.get("url"):
            return str(thumbnail["url"])
    for enclosure in getattr(entry, "enclosures", []) or []:
        if str(enclosure.get("type", "")).startswith("image/") and enclosure.get("href"):
            return str(enclosure["href"])
    return None


def _entry_categories(entry: object) -> list[str]:
    categories = [
        str(tag.get("term")) for tag in (getattr(entry, "tags", []) or []) if tag.get("term")
    ]
    return [category for category in categories if category][:8]


def parse_feed_bytes(
    payload: bytes, *, feed_language: str, settings: Settings, now: datetime | None = None
) -> list[ParsedEntry]:
    """Parse feed bytes into normalised entries, skipping anything unusable.

    A malformed entry is dropped with a debug line, never raised: one bad item
    must not cost us the other fifty in the same feed.
    """
    now = now or datetime.now(UTC)
    parsed = feedparser.parse(payload)
    entries: list[ParsedEntry] = []

    for raw in parsed.entries[: settings.ingest_max_entries_per_feed]:
        link = getattr(raw, "link", None)
        title = normalise_text(getattr(raw, "title", "") or "")
        if not link or not title:
            continue
        try:
            url_canonical = canonicalise_url(str(link))
        except ValueError:
            log.debug("entry_bad_url", url=str(link))
            continue

        summary = getattr(raw, "summary", None) or getattr(raw, "description", None)
        snippet = make_snippet(summary, settings.ingest_snippet_max_chars)
        declared = normalise_language_code(getattr(raw, "language", None)) or feed_language

        entries.append(
            ParsedEntry(
                url_canonical=url_canonical,
                title=title,
                snippet=snippet,
                image_url=_entry_image(raw),
                author_name=normalise_text(getattr(raw, "author", "") or "") or None,
                language=detect_language(f"{title} {snippet or ''}", fallback=declared),
                published_at=_entry_published(raw, now=now),
                raw_categories=_entry_categories(raw),
            )
        )
    return entries


async def fetch_feed(client: PoliteClient, feed: Feed, settings: Settings) -> FeedResult:
    """Fetch and parse one feed. Never raises - failure is a return value.

    That is deliberate: this runs inside a gather over hundreds of feeds, and
    an exception escaping here would take the batch with it.
    """
    headers: dict[str, str] = {}
    if feed.etag:
        headers["If-None-Match"] = feed.etag
    if feed.last_modified:
        headers["If-Modified-Since"] = feed.last_modified

    try:
        response = await client.get(feed.url, headers=headers)
    except httpx.HTTPError as exc:
        return FeedResult(feed.id, "failed", error=f"{type(exc).__name__}: {exc}")
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # a parse-time surprise must not kill the batch
        log.exception("feed_unexpected_error", feed_id=feed.id)
        return FeedResult(feed.id, "failed", error=f"{type(exc).__name__}: {exc}")

    if response is None:
        return FeedResult(feed.id, "skipped", error="robots.txt disallows this feed")
    if response.status_code == 304:
        return FeedResult(feed.id, "not_modified")
    if response.status_code >= 400:
        return FeedResult(feed.id, "failed", error=f"HTTP {response.status_code}")

    try:
        entries = parse_feed_bytes(response.content, feed_language=feed.language, settings=settings)
    except Exception as exc:
        log.exception("feed_parse_failed", feed_id=feed.id)
        return FeedResult(feed.id, "failed", error=f"parse: {type(exc).__name__}: {exc}")

    return FeedResult(
        feed.id,
        "ok",
        entries=entries,
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
    )
