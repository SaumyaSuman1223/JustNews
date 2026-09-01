"""Feed parsing and scheduling. No network, no database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from justnews_core.models import Feed
from justnews_core.settings import Settings
from justnews_ingestion.rss import (
    BACKOFF_MAX_MINUTES,
    backoff_until,
    is_due,
    parse_feed_bytes,
)

SETTINGS = Settings()

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Example</title>
  <item>
    <title>Central bank holds rates steady for a third consecutive meeting</title>
    <link>https://www.example.com/news/rates?utm_source=rss&amp;utm_medium=feed</link>
    <description>&lt;p&gt;The decision was widely expected by economists.&lt;/p&gt;</description>
    <pubDate>Mon, 31 Aug 2026 09:00:00 GMT</pubDate>
    <category>Business</category>
    <category>Economy</category>
    <author>Jane Roe</author>
  </item>
  <item>
    <title>No link here</title>
  </item>
  <item>
    <link>https://www.example.com/news/no-title</link>
  </item>
</channel></rss>
"""


class TestParseFeedBytes:
    def test_extracts_a_well_formed_entry(self) -> None:
        entries = parse_feed_bytes(RSS, feed_language="en", settings=SETTINGS)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.title.startswith("Central bank holds rates")
        assert entry.author_name == "Jane Roe"
        assert entry.raw_categories == ["Business", "Economy"]

    def test_canonicalises_the_link(self) -> None:
        entry = parse_feed_bytes(RSS, feed_language="en", settings=SETTINGS)[0]
        assert entry.url_canonical == "https://example.com/news/rates"

    def test_strips_html_from_the_description(self) -> None:
        entry = parse_feed_bytes(RSS, feed_language="en", settings=SETTINGS)[0]
        assert entry.snippet == "The decision was widely expected by economists."

    def test_skips_entries_missing_a_link_or_title(self) -> None:
        # One bad item must not cost us the good ones in the same feed.
        assert len(parse_feed_bytes(RSS, feed_language="en", settings=SETTINGS)) == 1

    def test_garbage_input_yields_no_entries_rather_than_raising(self) -> None:
        html = b"<html>not a feed</html>"
        assert parse_feed_bytes(html, feed_language="en", settings=SETTINGS) == []
        assert parse_feed_bytes(b"", feed_language="en", settings=SETTINGS) == []

    def test_respects_the_per_feed_entry_cap(self) -> None:
        items = "".join(
            f"<item><title>Headline number {i}</title><link>https://e.com/{i}</link></item>"
            for i in range(50)
        )
        payload = f"<rss version='2.0'><channel>{items}</channel></rss>".encode()
        settings = Settings(ingest_max_entries_per_feed=10)
        assert len(parse_feed_bytes(payload, feed_language="en", settings=settings)) == 10

    def test_future_timestamps_are_clamped_to_now(self) -> None:
        # Misconfigured feeds publish hours into the future. Left alone, those
        # articles pin themselves to the top of a recency feed indefinitely.
        future = (datetime.now(UTC) + timedelta(days=3)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        payload = (
            f"<rss version='2.0'><channel><item>"
            f"<title>A headline from the future</title>"
            f"<link>https://e.com/x</link><pubDate>{future}</pubDate>"
            f"</item></channel></rss>"
        ).encode()
        entry = parse_feed_bytes(payload, feed_language="en", settings=SETTINGS)[0]
        assert entry.published_at <= datetime.now(UTC) + timedelta(seconds=5)

    def test_missing_timestamp_defaults_to_now(self) -> None:
        payload = (
            b"<rss version='2.0'><channel><item><title>Undated headline here</title>"
            b"<link>https://e.com/y</link></item></channel></rss>"
        )
        entry = parse_feed_bytes(payload, feed_language="en", settings=SETTINGS)[0]
        assert (datetime.now(UTC) - entry.published_at) < timedelta(seconds=5)


class TestBackoff:
    def test_a_healthy_feed_is_due_immediately(self) -> None:
        now = datetime.now(UTC)
        assert backoff_until(0, now=now) == now

    def test_delay_grows_with_consecutive_failures(self) -> None:
        now = datetime.now(UTC)
        delays = [backoff_until(n, now=now) - now for n in (1, 2, 3, 4)]
        assert delays == sorted(delays)
        assert delays[0] < delays[-1]

    def test_delay_is_capped(self) -> None:
        # Without a cap, a feed that has been dead for a week is never retried.
        now = datetime.now(UTC)
        assert backoff_until(99, now=now) - now == timedelta(minutes=BACKOFF_MAX_MINUTES)


class TestIsDue:
    def _feed(self, **kwargs: object) -> Feed:
        return Feed(id=1, source_id=1, url="https://e.com/f", language="en", **kwargs)  # type: ignore[arg-type]

    def test_never_fetched_is_due(self) -> None:
        assert is_due(self._feed(active=True, consecutive_failures=0), now=datetime.now(UTC))

    def test_inactive_is_never_due(self) -> None:
        assert not is_due(self._feed(active=False, consecutive_failures=0), now=datetime.now(UTC))

    def test_a_failing_feed_waits_out_its_backoff(self) -> None:
        now = datetime.now(UTC)
        feed = self._feed(
            active=True, consecutive_failures=4, last_fetched_at=now - timedelta(minutes=5)
        )
        assert not is_due(feed, now=now)
        assert is_due(feed, now=now + timedelta(hours=6))


@pytest.mark.parametrize("language", ["en", "es", "ar", "zh"])
def test_declared_language_is_used_for_short_headlines(language: str) -> None:
    payload = (
        b"<rss version='2.0'><channel><item><title>Breve</title>"
        b"<link>https://e.com/z</link></item></channel></rss>"
    )
    entries = parse_feed_bytes(payload, feed_language=language, settings=SETTINGS)
    assert entries[0].language == language
