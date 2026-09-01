"""Integration test fixtures.

These run against a **real** PostgreSQL with pgvector - not a mock, not SQLite.
Half of what this codebase does (keyset pagination, ``ON CONFLICT`` upserts,
``tsvector``, vector similarity) has no meaningful behaviour on another engine,
so a test that avoids Postgres proves nothing.

Schema setup is deliberately **synchronous** and session-scoped, while the
engine tests use is asynchronous and function-scoped. Mixing those - a
session-scoped async engine shared across tests - binds asyncpg's connections
to the loop that created them, and every later test dies with "attached to a
different loop". Doing DDL over a sync driver sidesteps the problem entirely.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from justnews_core.models import Base
from justnews_core.settings import Settings, get_settings

TEST_DATABASE_SUFFIX = "_test"


def _test_url(async_driver: bool = True) -> str:
    """The development URL with ``_test`` appended to the database name, so a
    test run can never touch development data."""
    settings = get_settings()
    url = str(settings.database_url if async_driver else settings.sync_database_url)
    base, _, name = url.rpartition("/")
    return f"{base}/{name.split('?')[0]}{TEST_DATABASE_SUFFIX}"


@pytest.fixture(scope="session")
def database(request: pytest.FixtureRequest) -> Iterator[str]:
    """Create the test database and its schema once per session, synchronously."""
    sync_url = _test_url(async_driver=False)
    admin_url = str(get_settings().sync_database_url).rsplit("/", 1)[0] + "/postgres"
    test_db = sync_url.rsplit("/", 1)[1]

    admin = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{test_db}" WITH (FORCE)'))
            connection.execute(sa.text(f'CREATE DATABASE "{test_db}"'))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not reachable for integration tests: {exc}")
    finally:
        admin.dispose()

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    engine.dispose()

    yield _test_url()


@pytest.fixture
def truncate(database: str) -> Iterator[None]:
    """Empty every table after each test, synchronously."""
    yield
    engine = sa.create_engine(_test_url(async_driver=False))
    with engine.begin() as connection:
        tables = ",".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        connection.execute(sa.text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest_asyncio.fixture
async def engine(database: str, truncate: None) -> AsyncIterator[object]:
    """A fresh async engine per test, bound to this test's event loop."""
    test_engine = create_async_engine(database, poolclass=sa.pool.NullPool)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(engine: object) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with factory() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client(engine: object, database: str) -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to the app, with the app's sessions pointed at the
    test database."""
    from justnews_api.main import create_app
    from justnews_api.routers import content
    from justnews_testing.auth import FakeJWKSProvider

    settings = Settings(database_url=database)  # type: ignore[arg-type]
    factory = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    app = create_app(settings)
    # The real provider is built in the app's lifespan, which this fixture
    # never runs (see the get_session override just below - the same reason
    # applies: nothing here should reach a real network or database except
    # through this test's own engine). A fake keyed the same way lets
    # authenticated-route tests sign a real, verifiable token with no
    # Supabase project involved.
    app.state.jwks_provider = FakeJWKSProvider()

    async def override() -> AsyncIterator[AsyncSession]:
        async with factory() as db_session:
            yield db_session

    app.dependency_overrides[content.get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
