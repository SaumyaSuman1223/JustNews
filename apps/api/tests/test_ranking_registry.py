"""The ranking seam.

The point of the registry is that adding a ranker - Stage 6's FINDING model,
or whatever follows it - is a matter of writing one function and registering
it. These tests hold that promise to its word: a policy nobody anticipated is
registered here at test time, served through the unmodified request path, and
attributed correctly in the impression log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.services import feed as feed_service
from justnews_core.db import set_current_user
from justnews_core.models import Impression

FAKE_POLICY = "reverse_alphabetical_v0"


async def _reverse_alphabetical(
    session: AsyncSession, request: feed_service.PolicyRequest
) -> feed_service._UnloggedPage:
    """A deliberately silly ranker. Its job is to be obviously not the
    heuristic and obviously not chronological, so the assertions below cannot
    pass by accident."""
    rows = await feed_service.content_repo.list_articles_window(
        session,
        languages=request.languages,
        upper_bound=datetime.now(UTC),
        exclude_article_ids=request.excluded,
        limit=feed_service.CANDIDATE_POOL_SIZE,
    )
    ordered = sorted(rows, key=lambda row: row.title, reverse=True)
    return feed_service._UnloggedPage(articles=ordered[: request.page_size], next_cursor=None)


@pytest.fixture
def registered_policy() -> object:
    """Register the fake ranker for one test, then put the registry back.

    Mutating module state in a test is worth it here: registering a policy is
    exactly the operation under test, and doing it any other way would test a
    copy of the mechanism rather than the mechanism.
    """
    feed_service.POLICIES[FAKE_POLICY] = _reverse_alphabetical
    original = feed_service.EXPERIMENT_POLICIES
    feed_service.EXPERIMENT_POLICIES = (FAKE_POLICY,)
    yield
    feed_service.EXPERIMENT_POLICIES = original
    del feed_service.POLICIES[FAKE_POLICY]


class TestRegistry:
    def test_every_registered_policy_is_callable_with_the_shared_signature(self) -> None:
        for name, policy in feed_service.POLICIES.items():
            assert callable(policy), name

    def test_the_experiment_only_contains_registered_policies(self) -> None:
        # A reader bucketed into a policy that is not registered would be a
        # KeyError at serve time, on their request.
        assert set(feed_service.EXPERIMENT_POLICIES) <= set(feed_service.POLICIES)

    def test_assign_policy_only_returns_experiment_policies(self) -> None:
        seen = {feed_service.assign_policy(uuid.uuid4()) for _ in range(200)}
        assert seen <= set(feed_service.EXPERIMENT_POLICIES)

    def test_assign_policy_is_stable_for_a_reader(self) -> None:
        user_id = uuid.uuid4()
        first = feed_service.assign_policy(user_id)
        assert all(feed_service.assign_policy(user_id) == first for _ in range(10))


class TestServingAnUnanticipatedPolicy:
    async def test_a_newly_registered_policy_serves_and_is_logged_under_its_own_name(
        self,
        client: AsyncClient,
        session: AsyncSession,
        registered_policy: object,
    ) -> None:
        source = await make_source(session)
        for title in ("Alpha story", "Bravo story", "Charlie story"):
            await make_article(session, source, title=title)
        await session.commit()

        user_id = str(uuid.uuid4())
        headers = await make_beta_headers(session, user_id=user_id)
        response = await client.get("/v1/feed", headers=headers)

        assert response.status_code == 200
        titles = [item["article"]["title"] for item in response.json()["items"]]
        # Served by the fake ranker: reverse alphabetical, which neither of the
        # real policies would ever produce for this input.
        assert titles == ["Charlie story", "Bravo story", "Alpha story"]

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows, "the new policy must still log impressions"
        assert all(row.ranking_policy == FAKE_POLICY for row in rows)

    async def test_the_registry_is_restored_afterwards(self) -> None:
        # Guards the fixture itself: a leaked policy would silently re-bucket
        # every other test in the suite.
        assert FAKE_POLICY not in feed_service.POLICIES
        assert FAKE_POLICY not in feed_service.EXPERIMENT_POLICIES
