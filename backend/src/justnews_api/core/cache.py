"""A read-through cache in Upstash for anonymous, shareable reads.

Only for responses that are the same for every reader and log nothing: a
cached personal feed would replay a ranking - and its propensities - that no
policy decided for this request, which is exactly what CLAUDE.md's logging
rule exists to prevent. Every route that uses this states its TTL in ADR 0014.

Stale-while-revalidate: an entry is served fresh for ``ttl`` seconds and may
then be served stale for ``stale`` more while one request refreshes it in
the background, so a reader never waits on the database because an entry
expired a second ago. A short Redis lock makes that one request, not every
request that arrived during the refresh.

Redis being unconfigured, slow or down never fails a request: the loader
runs against the database as if there were no cache.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core import upstash
from justnews_core.db import get_session_factory
from justnews_core.logging import get_logger
from justnews_core.settings import Settings, get_settings

log = get_logger(__name__)

#: Bumped when a cached payload's shape changes, so a deploy never serves an
#: entry written by the previous version's models.
KEY_VERSION = "v1"
_REFRESH_LOCK_SECONDS = 30

Loader = Callable[[AsyncSession], Awaitable[Any]]

# Background refreshes are held here so the event loop does not collect a
# task that is still running.
_refreshes: set[asyncio.Task[None]] = set()


def _key(settings: Settings, name: str) -> str:
    # The environment is part of the key: a laptop or a staging deploy
    # pointed at the same Upstash database must never read - or write - the
    # entries production serves.
    return f"cache:{settings.app_env}:{KEY_VERSION}:{name}"


async def read_through(
    name: str,
    *,
    ttl: int,
    stale: int,
    session: AsyncSession,
    load: Loader,
    settings: Settings | None = None,
) -> Any:
    """The cached JSON value for ``name``, loading it with ``load`` on a miss.

    ``load`` must return something JSON-serialisable - a response model's
    ``model_dump(mode="json")``, not the model - and receives a session: the
    request's own on a miss, a fresh one for a background refresh, since the
    request's session is closed by the time a refresh runs.
    """
    settings = settings or get_settings()
    if not upstash.is_configured(settings):
        return await load(session)

    key = _key(settings, name)
    try:
        (raw,) = await upstash.pipeline(settings, [["GET", key]])
    except httpx.HTTPError as exc:
        log.warning("cache_read_failed", key=key, error=str(exc))
        return await load(session)

    if raw is not None:
        try:
            entry = json.loads(raw)
            value = entry["value"]
            fresh_until = float(entry["fresh_until"])
        except (ValueError, KeyError, TypeError):
            log.warning("cache_entry_unreadable", key=key)
        else:
            if time.time() >= fresh_until:
                _refresh_in_background(settings, key, ttl=ttl, stale=stale, load=load)
            return value

    value = await load(session)
    await _write(settings, key, value, ttl=ttl, stale=stale)
    return value


async def _write(settings: Settings, key: str, value: Any, *, ttl: int, stale: int) -> None:
    entry = json.dumps({"value": value, "fresh_until": time.time() + ttl})
    try:
        await upstash.pipeline(settings, [["SET", key, entry, "EX", str(ttl + stale)]])
    except httpx.HTTPError as exc:
        # The reader already has the value; a failed write only means the
        # next request loads it again.
        log.warning("cache_write_failed", key=key, error=str(exc))


def _refresh_in_background(
    settings: Settings, key: str, *, ttl: int, stale: int, load: Loader
) -> None:
    task = asyncio.create_task(_refresh(settings, key, ttl=ttl, stale=stale, load=load))
    _refreshes.add(task)
    task.add_done_callback(_refreshes.discard)


async def _refresh(settings: Settings, key: str, *, ttl: int, stale: int, load: Loader) -> None:
    try:
        (acquired,) = await upstash.pipeline(
            settings, [["SET", f"{key}:lock", "1", "NX", "EX", str(_REFRESH_LOCK_SECONDS)]]
        )
        if acquired is None:
            return  # Another request is already refreshing this entry.
        async with get_session_factory()() as session:
            value = await load(session)
        await _write(settings, key, value, ttl=ttl, stale=stale)
    except Exception as exc:
        # The stale entry keeps serving until it expires; logged so a refresh
        # that always fails is visible rather than silent.
        log.warning("cache_refresh_failed", key=key, error=str(exc))


async def drain() -> None:
    """Wait for in-flight refreshes - for shutdown, and for tests."""
    if _refreshes:
        await asyncio.gather(*_refreshes, return_exceptions=True)
