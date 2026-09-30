"""Test helper for the Stage 5 feed A/B split.

``services.feed.assign_policy`` buckets every reader deterministically by
their user id, which is exactly right for a real experiment and exactly
wrong for an ordering-sensitive test that does not want a coin flip deciding
whether it passes. This finds a user id that lands in the bucket a test
actually wants to exercise.
"""

from __future__ import annotations

import uuid

import pytest

from justnews_api.services import feed
from justnews_api.services.feed import assign_policy


def find_user_id_for_policy(policy: str) -> str:
    for _ in range(1000):
        candidate = uuid.uuid4()
        if assign_policy(candidate) == policy:
            return str(candidate)
    raise RuntimeError(f"could not find a user id for policy {policy!r}")


@pytest.fixture
def v1_in_experiment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Puts ranker v1 back in the A/B split for one test.

    v1 left the split when v2 replaced it (ADR 0015) but stays registered as
    the rollback, so its own tests still exercise it through the unmodified
    request path - by bucketing readers into it, as the split once did.
    """
    monkeypatch.setattr(
        feed,
        "EXPERIMENT_SPLIT",
        ((feed.HEURISTIC_POLICY, 50), (feed.CHRONOLOGICAL_POLICY, 50)),
    )
