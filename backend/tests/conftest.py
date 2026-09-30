"""Database fixtures come from the shared testing package."""

import pytest
from justnews_testing.fixtures import (  # noqa: F401
    client,
    database,
    engine,
    session,
    truncate,
)
from justnews_testing.policy import v1_in_experiment  # noqa: F401

from justnews_api.services import recommend


@pytest.fixture(autouse=True)
def _fresh_vector_cache() -> None:
    """Ranker v2 keeps article vectors for the life of the process, which is
    right in production - an article id is never reused - and wrong here,
    where every test truncates with RESTART IDENTITY."""
    recommend._VECTORS.clear()
