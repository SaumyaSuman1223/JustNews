"""Test helper for the Stage 5 feed A/B split.

``services.feed.assign_policy`` buckets every reader deterministically by
their user id, which is exactly right for a real experiment and exactly
wrong for an ordering-sensitive test that does not want a coin flip deciding
whether it passes. This finds a user id that lands in the bucket a test
actually wants to exercise.
"""

from __future__ import annotations

import uuid

from justnews_api.services.feed import assign_policy


def find_user_id_for_policy(policy: str) -> str:
    for _ in range(1000):
        candidate = uuid.uuid4()
        if assign_policy(candidate) == policy:
            return str(candidate)
    raise RuntimeError(f"could not find a user id for policy {policy!r}")
