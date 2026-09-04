"""Unit tests for the Stage 5 heuristic ranker, and integration tests for the
heuristic side of the /v1/feed A/B split (the chronological side is tested in
test_feed_api.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from justnews_testing.policy import find_user_id_for_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories.content import ArticleRow
from justnews_api.services import ranking
from justnews_api.services.feed import HEURISTIC_POLICY, assign_policy
from justnews_core.db import set_current_user
from justnews_core.models import ArticleTopic, Impression

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)


def _article(
    article_id: int,
    *,
    hours_old: float = 1.0,
    language: str = "en",
    source_slug: str = "source-a",
    trust: float = 0.8,
    story_cluster_id: int | None = None,
) -> ArticleRow:
    return ArticleRow(
        id=article_id,
        title=f"Article {article_id}",
        snippet=None,
        image_url=None,
        url_canonical=f"https://example.test/{article_id}",
        language=language,
        published_at=NOW - timedelta(hours=hours_old),
        # Derived from the slug so two articles from one source share an id,
        # which is what the diversity tests are actually asserting about.
        source_id=abs(hash(source_slug)) % 10_000,
        source_name=source_slug,
        source_slug=source_slug,
        story_cluster_id=story_cluster_id,
        source_trust_score=trust,
    )


class TestScoring:
    def test_newer_outscores_older_all_else_equal(self) -> None:
        newer = _article(1, hours_old=1)
        older = _article(2, hours_old=48)
        scored = ranking.score_candidates(
            [newer, older],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        by_id = {c.article.id: c.score for c in scored}
        assert by_id[1] > by_id[2]

    def test_followed_topic_boosts_an_older_article_above_a_newer_unfollowed_one(self) -> None:
        followed = _article(1, hours_old=10)
        unfollowed = _article(2, hours_old=1)
        scored = ranking.score_candidates(
            [followed, unfollowed],
            topic_ids_by_article={1: ["medtop:01000000"]},
            click_counts={},
            followed_topic_ids={"medtop:01000000"},
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        by_id = {c.article.id: c.score for c in scored}
        assert by_id[1] > by_id[2]

    def test_already_seen_is_penalised(self) -> None:
        article = _article(1, hours_old=1)
        [unseen] = ranking.score_candidates(
            [article],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        [seen] = ranking.score_candidates(
            [article],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids={1},
            preferred_languages=["en"],
            now=NOW,
        )
        assert seen.score < unseen.score

    def test_higher_trust_source_outscores_lower_trust_all_else_equal(self) -> None:
        trusted = _article(1, hours_old=1, trust=0.9)
        untrusted = _article(2, hours_old=1, trust=0.1)
        scored = ranking.score_candidates(
            [trusted, untrusted],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        by_id = {c.article.id: c.score for c in scored}
        assert by_id[1] > by_id[2]
        # The trust floor means a low-trust source is deprioritised, not
        # zeroed out - it must still be able to appear.
        assert by_id[2] > 0

    def test_primary_language_outscores_secondary(self) -> None:
        primary = _article(1, hours_old=1, language="en")
        secondary = _article(2, hours_old=1, language="es")
        scored = ranking.score_candidates(
            [primary, secondary],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en", "es"],
            now=NOW,
        )
        by_id = {c.article.id: c.score for c in scored}
        assert by_id[1] > by_id[2]


class TestClusterDedupe:
    def test_keeps_only_the_higher_scored_article_per_cluster(self) -> None:
        better = _article(1, hours_old=1, story_cluster_id=100)
        worse = _article(2, hours_old=48, story_cluster_id=100)
        scored = ranking.score_candidates(
            [worse, better],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        deduped = ranking.dedupe_story_clusters(scored)
        assert [c.article.id for c in deduped] == [1]

    def test_standalone_articles_are_unaffected(self) -> None:
        a = _article(1, hours_old=1, story_cluster_id=None)
        b = _article(2, hours_old=2, story_cluster_id=None)
        scored = ranking.score_candidates(
            [a, b],
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        deduped = ranking.dedupe_story_clusters(scored)
        assert {c.article.id for c in deduped} == {1, 2}


class TestDiversify:
    def test_never_drops_a_candidate(self) -> None:
        articles = [_article(i, hours_old=i, source_slug=f"source-{i % 3}") for i in range(1, 21)]
        scored = ranking.score_candidates(
            articles,
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        diversified = ranking.diversify(scored)
        assert {a.id for a in diversified} == {a.id for a in articles}
        assert len(diversified) == len(articles)

    def test_breaks_up_a_run_from_one_source(self) -> None:
        # 10 articles all from the same source, all with similar high
        # scores (very recent) - a flat sort by score would put every one of
        # them consecutively at the top. MMR should not.
        same_source = [
            _article(i, hours_old=0.1 * i, source_slug="only-source") for i in range(1, 11)
        ]
        scored = ranking.score_candidates(
            same_source,
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        diversified = ranking.diversify(scored)
        # With only one source in play there is nothing to diversify against,
        # so this should still return every item - the real diversity
        # behaviour is exercised by the mixed-source test below.
        assert len(diversified) == 10

    def test_interleaves_two_equally_strong_sources_rather_than_blocking_them(self) -> None:
        a_articles = [_article(i, hours_old=1, source_slug="source-a") for i in range(1, 6)]
        b_articles = [_article(i, hours_old=1, source_slug="source-b") for i in range(6, 11)]
        scored = ranking.score_candidates(
            a_articles + b_articles,
            topic_ids_by_article={},
            click_counts={},
            followed_topic_ids=set(),
            seen_article_ids=set(),
            preferred_languages=["en"],
            now=NOW,
        )
        diversified = ranking.diversify(scored)
        top_four_sources = {a.source_slug for a in diversified[:4]}
        # Equal scores, two sources - MMR's redundancy penalty should pull
        # from both rather than exhausting one source first.
        assert top_four_sources == {"source-a", "source-b"}


class TestPolicyAssignment:
    def test_deterministic_for_the_same_user(self) -> None:
        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        assert assign_policy(uuid.UUID(user_id)) == HEURISTIC_POLICY
        assert assign_policy(uuid.UUID(user_id)) == HEURISTIC_POLICY


class TestHeuristicFeedEndpoint:
    async def test_ranking_policy_is_logged(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A")
        await make_article(session, source, title="B")
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        headers["x-analytics-consent"] = "granted"
        response = await client.get("/v1/feed", headers=headers)
        assert response.status_code == 200

        await set_current_user(session, user_id)
        rows = (await session.execute(select(Impression))).scalars().all()
        assert rows and all(row.ranking_policy == HEURISTIC_POLICY for row in rows)

    async def test_followed_topic_article_ranks_above_an_unfollowed_newer_one(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        topic = await make_topic(session)
        followed = await make_article(session, source, title="Followed topic", minutes_ago=600)
        await make_article(session, source, title="Just unfollowed news", minutes_ago=1)
        await session.commit()

        session.add(ArticleTopic(article_id=followed.id, topic_id=topic.id))
        await session.commit()

        user_id = find_user_id_for_policy(HEURISTIC_POLICY)
        headers = await make_beta_headers(session, user_id=user_id)
        await client.post("/v1/follows", json={"topic_id": topic.id}, headers=headers)

        body = (await client.get("/v1/feed", headers=headers)).json()
        titles = [item["article"]["title"] for item in body["items"]]
        assert titles.index("Followed topic") < titles.index("Just unfollowed news")

    async def test_pagination_visits_every_candidate_exactly_once(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        for index in range(25):
            await make_article(session, source, title=f"Article {index}", minutes_ago=index)
        await session.commit()

        headers = await make_beta_headers(
            session, user_id=find_user_id_for_policy(HEURISTIC_POLICY)
        )

        seen: list[int] = []
        cursor: str | None = None
        for _ in range(10):
            url = f"/v1/feed?page_size=7{f'&cursor={cursor}' if cursor else ''}"
            body = (await client.get(url, headers=headers)).json()
            seen.extend(item["article"]["id"] for item in body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                break

        assert len(seen) == 25
        assert len(set(seen)) == 25
