"""A read-through cache for anonymous, shareable reads: this process's own
memory first, then Upstash.

Only for responses that are the same for every reader and log nothing: a
cached personal feed would replay a ranking - and its propensities - that no
policy decided for this request, which is exactly what CLAUDE.md's logging
rule exists to prevent. Every route that uses this states its TTL in ADR 0014.

Two layers, one policy:

- **In process.** A bounded map in this process. A hit costs no round trip at
  all, and it needs no service: the API ran for weeks with Upstash never
  connected, which with Redis as the only layer meant no cache whatsoever -
  every read paid four to ten database round trips across an ocean. One API
  process is its own complete cache; this is the layer that is always there.
- **Upstash**, when configured: what a second process, or this one after a
  restart, reads instead of the database.

Stale-while-revalidate, in both: an entry is served fresh for ``ttl`` seconds
and may then be served stale for ``stale`` more while one request refreshes
it in the background, so a reader never waits on the database because an
entry expired a second ago. One refresh per key per process, and with Redis
a short lock makes that one refresh across processes too.

Neither layer can fail a request. Redis unconfigured, slow or down: the
loader runs against the database. The in-process layer off (local
development and tests - `Settings.in_process_cache`): the same.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class _Local:
    #: Kept serialised and parsed on every hit, as a Redis entry is: each
    #: request gets its own object, so nothing one caller does to a response
    #: can reach the next reader's.
    payload: str
    fresh_until: float
    stale_until: float


# Least recently used first. Bounded by `Settings.read_cache_max_entries`:
# keys carry query parameters, so the set of them is not closed.
_local: OrderedDict[str, _Local] = OrderedDict()

# Background refreshes are held here so the event loop does not collect a
# task that is still running; `_refreshing` is the per-process half of "one
# refresh per key".
_refreshes: set[asyncio.Task[None]] = set()
_refreshing: set[str] = set()


def _key(settings: Settings, name: str) -> str:
    # The environment is part of the key: a laptop or a staging deploy
    # pointed at the same Upstash database must never read - or write - the
    # entries production serves.
    return f"cache:{settings.app_env}:{KEY_VERSION}:{name}"


def _local_get(key: str, now: float) -> _Local | None:
    entry = _local.get(key)
    if entry is None:
        return None
    if now >= entry.stale_until:
        del _local[key]
        return None
    _local.move_to_end(key)
    return entry


def _local_put(
    settings: Settings, key: str, payload: str, *, fresh_until: float, stale_until: float
) -> None:
    if not settings.in_process_cache:
        return
    _local[key] = _Local(payload=payload, fresh_until=fresh_until, stale_until=stale_until)
    _local.move_to_end(key)
    while len(_local) > settings.read_cache_max_entries:
        _local.popitem(last=False)


def clear_local() -> None:
    """Forget everything this process holds - for tests."""
    _local.clear()


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
    key = _key(settings, name)
    now = time.time()

    if settings.in_process_cache:
        local = _local_get(key, now)
        if local is not None:
            if now >= local.fresh_until:
                _refresh_in_background(settings, key, ttl=ttl, stale=stale, load=load)
            return json.loads(local.payload)

    if upstash.is_configured(settings):
        found, value = await _read_redis(settings, key, now, ttl=ttl, stale=stale, load=load)
        if found:
            return value

    value = await load(session)
    await _store(settings, key, value, ttl=ttl, stale=stale)
    return value


async def _read_redis(
    settings: Settings, key: str, now: float, *, ttl: int, stale: int, load: Loader
) -> tuple[bool, Any]:
    """``(True, value)`` for an entry Redis holds; ``(False, None)`` for a
    miss, an unreadable entry or an unreachable Redis."""
    try:
        (raw,) = await upstash.pipeline(settings, [["GET", key]])
    except httpx.HTTPError as exc:
        log.warning("cache_read_failed", key=key, error=str(exc))
        return False, None
    if raw is None:
        return False, None
    try:
        entry = json.loads(raw)
        value = entry["value"]
        fresh_until = float(entry["fresh_until"])
    except (ValueError, KeyError, TypeError):
        log.warning("cache_entry_unreadable", key=key)
        return False, None
    # Redis expires the key at the end of its stale window, so an entry that
    # is still there is still servable; this process keeps it that long too.
    _local_put(
        settings,
        key,
        json.dumps(value),
        fresh_until=fresh_until,
        stale_until=fresh_until + stale,
    )
    if now >= fresh_until:
        _refresh_in_background(settings, key, ttl=ttl, stale=stale, load=load)
    return True, value


async def _adopt_fresh(settings: Settings, key: str, *, stale: int) -> bool:
    """Copies Redis's entry into this process if it is still fresh."""
    try:
        (raw,) = await upstash.pipeline(settings, [["GET", key]])
        if raw is None:
            return False
        entry = json.loads(raw)
        value = entry["value"]
        fresh_until = float(entry["fresh_until"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return False
    if time.time() >= fresh_until:
        return False
    _local_put(
        settings,
        key,
        json.dumps(value),
        fresh_until=fresh_until,
        stale_until=fresh_until + stale,
    )
    return True


async def _store(settings: Settings, key: str, value: Any, *, ttl: int, stale: int) -> None:
    fresh_until = time.time() + ttl
    _local_put(
        settings, key, json.dumps(value), fresh_until=fresh_until, stale_until=fresh_until + stale
    )
    if not upstash.is_configured(settings):
        return
    entry = json.dumps({"value": value, "fresh_until": fresh_until})
    try:
        await upstash.pipeline(settings, [["SET", key, entry, "EX", str(ttl + stale)]])
    except httpx.HTTPError as exc:
        # The reader already has the value; a failed write only means the
        # next process to ask loads it again.
        log.warning("cache_write_failed", key=key, error=str(exc))


def _refresh_in_background(
    settings: Settings, key: str, *, ttl: int, stale: int, load: Loader
) -> None:
    if key in _refreshing:
        return  # This process is already refreshing this entry.
    _refreshing.add(key)
    task = asyncio.create_task(_refresh(settings, key, ttl=ttl, stale=stale, load=load))
    _refreshes.add(task)
    task.add_done_callback(_refreshes.discard)


async def _refresh(settings: Settings, key: str, *, ttl: int, stale: int, load: Loader) -> None:
    try:
        if upstash.is_configured(settings):
            # A refresh started from this process's own stale copy has not
            # looked at Redis yet: another process may already have
            # refreshed the entry, and then its copy is taken as it is, with
            # no database read.
            if settings.in_process_cache and await _adopt_fresh(settings, key, stale=stale):
                return
            (acquired,) = await upstash.pipeline(
                settings, [["SET", f"{key}:lock", "1", "NX", "EX", str(_REFRESH_LOCK_SECONDS)]]
            )
            if acquired is None:
                return  # Another process is already refreshing this entry.
        async with get_session_factory()() as session:
            value = await load(session)
        await _store(settings, key, value, ttl=ttl, stale=stale)
    except Exception as exc:
        # The stale entry keeps serving until it expires; logged so a refresh
        # that always fails is visible rather than silent.
        log.warning("cache_refresh_failed", key=key, error=str(exc))
    finally:
        _refreshing.discard(key)


async def drain() -> None:
    """Wait for in-flight refreshes - for shutdown, and for tests."""
    if _refreshes:
        await asyncio.gather(*_refreshes, return_exceptions=True)
