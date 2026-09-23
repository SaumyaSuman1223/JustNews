"""Unit tests for the Upstash read-through cache.

Upstash is replaced by an in-memory stand-in for ``upstash.pipeline``: what is
under test is the cache's policy - fresh, stale, missing, broken - not the
REST call. The background refresh opens its own session, so the session
factory is replaced as well; no loader here touches a database.
"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
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

    async def pipeline(self, settings: Settings, commands: list[list[str]]) -> list[Any]:
        if self.broken:
            raise httpx.ConnectError("no route to host")
        results: list[Any] = []
        for command in commands:
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
