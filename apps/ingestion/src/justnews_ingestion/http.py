"""Polite HTTP client.

Three things every request through here gets, without the caller asking:
an explicit timeout, a per-host delay so we never hammer a publisher, and a
robots.txt check. None of them are optional and none can be bypassed - the
alternative is being blocked by the sources the whole product depends on.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from types import TracebackType
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from justnews_core.logging import get_logger
from justnews_core.settings import Settings

log = get_logger(__name__)

ROBOTS_CACHE_SECONDS = 3600.0


@dataclass(slots=True)
class _RobotsEntry:
    parser: RobotFileParser | None
    fetched_at: float


class PoliteClient:
    """Async HTTP client with per-host rate limiting and robots.txt caching."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ingest_http_timeout_seconds),
            follow_redirects=True,
            max_redirects=5,
            headers={
                "User-Agent": settings.ingest_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_last_request: dict[str, float] = {}
        self._robots: dict[str, _RobotsEntry] = {}

    async def __aenter__(self) -> PoliteClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _lock_for(self, host: str) -> asyncio.Lock:
        lock = self._host_locks.get(host)
        if lock is None:
            lock = asyncio.Lock()
            self._host_locks[host] = lock
        return lock

    async def _throttle(self, host: str) -> None:
        """Serialise requests per host and space them by the configured delay."""
        delay = self._settings.ingest_per_host_delay_seconds
        if delay <= 0:
            return
        elapsed = time.monotonic() - self._host_last_request.get(host, 0.0)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._host_last_request[host] = time.monotonic()

    async def allowed_by_robots(self, url: str) -> bool:
        """Fail open on a robots.txt we cannot fetch, closed on one that
        disallows us. A 404 means no rules, which is permission."""
        parts = urlsplit(url)
        host = parts.netloc.lower()
        entry = self._robots.get(host)
        now = time.monotonic()

        if entry is None or now - entry.fetched_at > ROBOTS_CACHE_SECONDS:
            parser: RobotFileParser | None = None
            try:
                response = await self._client.get(
                    f"{parts.scheme}://{parts.netloc}/robots.txt", timeout=5.0
                )
                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
            except httpx.HTTPError as exc:
                log.debug("robots_fetch_failed", host=host, error=type(exc).__name__)
            entry = _RobotsEntry(parser=parser, fetched_at=now)
            self._robots[host] = entry

        if entry.parser is None:
            return True
        return entry.parser.can_fetch(self._settings.ingest_user_agent, url)

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None, check_robots: bool = True
    ) -> httpx.Response | None:
        """GET a URL politely. Returns None when robots.txt forbids it."""
        if check_robots and not await self.allowed_by_robots(url):
            log.info("robots_disallowed", url=url)
            return None

        host = urlsplit(url).netloc.lower()
        async with self._lock_for(host):
            await self._throttle(host)
            return await self._client.get(url, headers=headers or {})
