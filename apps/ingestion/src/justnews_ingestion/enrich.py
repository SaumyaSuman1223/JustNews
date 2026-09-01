"""Metadata enrichment.

Fetches a page only to read its ``<head>``: the publisher's own canonical URL,
an OG image and an author. **Metadata only** - we never extract, store or
republish article body text, and there is deliberately no function here that
could.

Enrichment is best-effort by design. A feed already gave us a usable article;
this only improves it, so every failure is swallowed and logged.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from justnews_core.logging import get_logger
from justnews_core.settings import Settings
from justnews_core.text import canonicalise_url, make_snippet, normalise_text
from justnews_ingestion.http import PoliteClient

log = get_logger(__name__)

MAX_HTML_BYTES = 512_000


@dataclass(frozen=True, slots=True)
class Metadata:
    canonical_url: str | None = None
    image_url: str | None = None
    author_name: str | None = None
    description: str | None = None


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            value = normalise_text(str(tag["content"]))
            if value:
                return value
    return None


def parse_metadata(html: str, settings: Settings) -> Metadata:
    soup = BeautifulSoup(html, "lxml")

    canonical: str | None = None
    link = soup.find("link", attrs={"rel": "canonical"})
    href = link.get("href") if link else None
    if href:
        try:
            canonical = canonicalise_url(str(href))
        except ValueError:
            canonical = None

    description = _meta(soup, "og:description", "twitter:description", "description")
    return Metadata(
        canonical_url=canonical,
        image_url=_meta(soup, "og:image", "twitter:image", "twitter:image:src"),
        author_name=_meta(soup, "article:author", "author"),
        description=make_snippet(description, settings.ingest_snippet_max_chars),
    )


async def enrich(client: PoliteClient, url: str, settings: Settings) -> Metadata:
    """Best-effort. Returns empty metadata on any failure, never raises."""
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        log.debug("enrich_fetch_failed", url=url, error=type(exc).__name__)
        return Metadata()

    if response is None or response.status_code >= 400:
        return Metadata()
    if "html" not in response.headers.get("content-type", ""):
        return Metadata()

    try:
        return parse_metadata(response.text[:MAX_HTML_BYTES], settings)
    except Exception as exc:
        log.debug("enrich_parse_failed", url=url, error=type(exc).__name__)
        return Metadata()
