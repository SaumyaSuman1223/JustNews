"""Unit tests for the read-through cache: Upstash, and the in-process layer
in front of it.

Upstash is replaced by an in-memory stand-in for ``upstash.pipeline``: what is
under test is the cache's policy - fresh, stale, missing, broken - not the
REST call. The background refresh opens its own session, so the session
factory is replaced as well; no loader here touches a database.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from justnews_api.core import cache, upstash
from justnews_core.settings import Settings

SETTINGS = Settings(  # type: ignore[call-arg]
    upstash_redis_rest_url="https://fake-upstash.example",
    upstash_redis_rest_token="fake-token",
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.broken = False
        self.commands: list[str] = []

    async def pipeline(self, settings: Settings, commands: list[list[str]]) -> list[Any]:
        if self.broken:
            raise httpx.ConnectError("no route to host")
        results: list[Any] = []
        for command in commands:
            self.commands.append(command[0])
            if command[0] == "GET":
                results.append(self.store.get(command[1]))
            elif command[0] == "SET" and "NX" in command:
                if command[1] in self.store:
                    results.append(None)
                else:
                    self.store[command[1]] = command[2]
                    results.append("OK")
            elif command[0] == "SET":
                self.store[command[1]] = command[2]
                results.append("OK")
        return results


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(upstash, "pipeline", fake.pipeline)

    @asynccontextmanager
    async def no_session():  # type: ignore[no-untyped-def]
        yield None

    monkeypatch.setattr(cache, "get_session_factory", lambda: no_session)
    return fake


class Loader:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.calls = 0

    async def __call__(self, session: Any) -> Any:
        self.calls += 1
        return self.value


async def _read(loader: Loader, *, ttl: int = 60) -> Any:
    return await cache.read_through(
        "thing",
        ttl=ttl,
        stale=300,
        session=None,  # type: ignore[arg-type]
        load=loader,
        settings=SETTINGS,
    )


class TestReadThrough:
    async def test_a_miss_loads_and_stores(self, redis: FakeRedis) -> None:
        loader = Loader({"n": 1})
        assert await _read(loader) == {"n": 1}
        assert loader.calls == 1
        assert json.loads(redis.store["cache:local:v1:thing"])["value"] == {"n": 1}

    async def test_a_fresh_hit_does_not_load(self, redis: FakeRedis) -> None:
        await _read(Loader({"n": 1}))
        second = Loader({"n": 2})
        assert await _read(second) == {"n": 1}
        assert second.calls == 0

    async def test_a_stale_hit_serves_stale_and_refreshes_once(self, redis: FakeRedis) -> None:
        redis.store["cache:local:v1:thing"] = json.dumps(
            {"value": {"n": 1}, "fresh_until": time.time() - 1}
        )
        refreshed = Loader({"n": 2})
        assert await _read(refreshed) == {"n": 1}
        assert await _read(refreshed) == {"n": 1}
        await cache.drain()
        # The lock let one of the two stale reads refresh, not both.
        assert refreshed.calls == 1
        assert json.loads(redis.store["cache:local:v1:thing"])["value"] == {"n": 2}

    async def test_redis_down_falls_back_to_the_loader(self, redis: FakeRedis) -> None:
        redis.broken = True
        loader = Loader({"n": 1})
        assert await _read(loader) == {"n": 1}
        assert loader.calls == 1

    async def test_an_unreadable_entry_is_reloaded(self, redis: FakeRedis) -> None:
        redis.store["cache:local:v1:thing"] = "not json"
        loader = Loader({"n": 1})
        assert await _read(loader) == {"n": 1}
        assert loader.calls == 1

    async def test_a_null_payload_is_cached_as_null(self, redis: FakeRedis) -> None:
        # "No issue published yet" is a real answer and worth caching too.
        await _read(Loader(None))
        second = Loader({"n": 2})
        assert await _read(second) is None
        assert second.calls == 0

    async def test_unconfigured_is_a_plain_load(self) -> None:
        loader = Loader({"n": 1})
        value = await cache.read_through(
            "thing",
            ttl=60,
            stale=300,
            session=None,  # type: ignore[arg-type]
            load=loader,
            settings=Settings(),  # type: ignore[call-arg]
        )
        assert value == {"n": 1}
        assert loader.calls == 1
        # Off locally, so a second read is a second load: nothing a test or a
        # developer writes is hidden behind an earlier response.
        await cache.read_through(
            "thing",
            ttl=60,
            stale=300,
            session=None,  # type: ignore[arg-type]
            load=loader,
            settings=Settings(),  # type: ignore[call-arg]
        )
        assert loader.calls == 2


# --- the in-process layer -----------------------------------------------------

#: One API process and no Redis at all - how production ran for weeks, and
#: what the in-process layer exists for.
MEMORY_ONLY = Settings(read_cache_in_process=True)  # type: ignore[call-arg]
BOTH = Settings(  # type: ignore[call-arg]
    upstash_redis_rest_url="https://fake-upstash.example",
    upstash_redis_rest_token="fake-token",
    read_cache_in_process=True,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(cache, "time", SimpleNamespace(time=lambda: fake.now))
    return fake


@pytest.fixture(autouse=True)
def _empty_memory(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    @asynccontextmanager
    async def no_session():  # type: ignore[no-untyped-def]
        yield None

    monkeypatch.setattr(cache, "get_session_factory", lambda: no_session)
    cache.clear_local()
    yield
    cache.clear_local()


async def _read_with(settings: Settings, loader: Loader, name: str = "thing") -> Any:
    return await cache.read_through(
        name,
        ttl=60,
        stale=300,
        session=None,  # type: ignore[arg-type]
        load=loader,
        settings=settings,
    )


class TestInProcess:
    def test_on_wherever_readers_are_served_and_off_locally(self) -> None:
        assert Settings(app_env="local").in_process_cache is False  # type: ignore[call-arg]
        assert Settings(app_env="staging").in_process_cache is True  # type: ignore[call-arg]
        assert Settings(app_env="production").in_process_cache is True  # type: ignore[call-arg]
        # An explicit choice wins either way.
        assert (
            Settings(app_env="production", read_cache_in_process=False).in_process_cache  # type: ignore[call-arg]
            is False
        )

    async def test_without_redis_a_second_read_does_not_load(self, clock: Clock) -> None:
        loader = Loader({"n": 1})
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 1}
        clock.advance(59)
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 1}
        assert loader.calls == 1

    async def test_each_read_gets_its_own_object(self, clock: Clock) -> None:
        loader = Loader({"items": [1]})
        first = await _read_with(MEMORY_ONLY, loader)
        first["items"].append(2)
        assert await _read_with(MEMORY_ONLY, loader) == {"items": [1]}

    async def test_a_null_payload_is_remembered_as_null(self, clock: Clock) -> None:
        loader = Loader(None)
        assert await _read_with(MEMORY_ONLY, loader) is None
        assert await _read_with(MEMORY_ONLY, loader) is None
        assert loader.calls == 1

    async def test_a_stale_entry_is_served_and_refreshed_once(self, clock: Clock) -> None:
        loader = Loader({"n": 1})
        await _read_with(MEMORY_ONLY, loader)
        loader.value = {"n": 2}
        clock.advance(61)
        # Two readers arrive while it is stale: both get the old value at
        # once, and one refresh runs behind them.
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 1}
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 1}
        await cache.drain()
        assert loader.calls == 2
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 2}
        assert loader.calls == 2

    async def test_past_its_stale_window_an_entry_is_loaded_again(self, clock: Clock) -> None:
        loader = Loader({"n": 1})
        await _read_with(MEMORY_ONLY, loader)
        loader.value = {"n": 2}
        clock.advance(60 + 300 + 1)
        # Too old to show anyone: this reader waits for the real answer.
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 2}
        assert loader.calls == 2

    async def test_a_failed_refresh_keeps_serving_the_stale_entry(self, clock: Clock) -> None:
        loader = Loader({"n": 1})
        await _read_with(MEMORY_ONLY, loader)
        clock.advance(61)

        async def broken(session: Any) -> Any:
            raise RuntimeError("database is down")

        assert await _read_with(MEMORY_ONLY, broken) == {"n": 1}  # type: ignore[arg-type]
        await cache.drain()
        # And the next stale read may try again - the failure released the key.
        assert await _read_with(MEMORY_ONLY, loader) == {"n": 1}
        await cache.drain()
        assert loader.calls == 2

    async def test_the_least_recently_used_entry_is_dropped_at_the_bound(
        self, clock: Clock
    ) -> None:
        small = Settings(read_cache_in_process=True, read_cache_max_entries=2)  # type: ignore[call-arg]
        loaders = {name: Loader(name) for name in ("a", "b", "c")}
        await _read_with(small, loaders["a"], "a")
        await _read_with(small, loaders["b"], "b")
        await _read_with(small, loaders["a"], "a")  # "a" is now the more recent
        await _read_with(small, loaders["c"], "c")  # which pushes "b" out
        await _read_with(small, loaders["a"], "a")
        await _read_with(small, loaders["b"], "b")
        assert (loaders["a"].calls, loaders["b"].calls, loaders["c"].calls) == (1, 2, 1)

    async def test_an_empty_process_reads_redis_not_the_database(
        self, redis: FakeRedis, clock: Clock
    ) -> None:
        # After a restart, or in a second process: Redis has it.
        redis.store["cache:local:v1:thing"] = json.dumps(
            {"value": {"n": 1}, "fresh_until": clock.now + 30}
        )
        loader = Loader({"n": 2})
        assert await _read_with(BOTH, loader) == {"n": 1}
        assert await _read_with(BOTH, loader) == {"n": 1}
        assert loader.calls == 0
        # The second read never left the process.
        assert redis.commands == ["GET"]

    async def test_a_load_is_written_to_both_layers(self, redis: FakeRedis, clock: Clock) -> None:
        loader = Loader({"n": 1})
        await _read_with(BOTH, loader)
        assert json.loads(redis.store["cache:local:v1:thing"])["value"] == {"n": 1}
        redis.broken = True  # Redis going away changes nothing for this process
        assert await _read_with(BOTH, loader) == {"n": 1}
        assert loader.calls == 1

    async def test_a_refresh_takes_another_processs_fresh_entry_over_a_database_read(
        self, redis: FakeRedis, clock: Clock
    ) -> None:
        loader = Loader({"n": 1})
        await _read_with(BOTH, loader)
        clock.advance(61)
        # Meanwhile another process refreshed the entry in Redis.
        redis.store["cache:local:v1:thing"] = json.dumps(
            {"value": {"n": 2}, "fresh_until": clock.now + 60}
        )
        assert await _read_with(BOTH, loader) == {"n": 1}
        await cache.drain()
        assert await _read_with(BOTH, loader) == {"n": 2}
        assert loader.calls == 1
