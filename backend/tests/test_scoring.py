"""Ranker v2's arithmetic (services/scoring.py): pure functions, no database."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from justnews_api.services import scoring
from justnews_api.services.scoring import Candidate, Sampling, Signals

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def _candidate(article_id: int, **overrides: object) -> Candidate:
    values: dict[str, object] = {
        "article_id": article_id,
        "source_id": article_id,
        "story_cluster_id": None,
        "language": "en",
        "published_at": NOW - timedelta(hours=1),
        "trust": 0.8,
        "sources": 1,
        "languages": 1,
        "topic_ids": frozenset(),
        "similarity": None,
    }
    values.update(overrides)
    return Candidate(**values)  # type: ignore[arg-type]


def _score(candidate: Candidate, signals: Signals | None = None) -> float:
    return scoring.score(candidate, signals or Signals(), scoring.FOR_YOU, now=NOW)


class TestScore:
    def test_newer_scores_higher(self) -> None:
        old = _candidate(1, published_at=NOW - timedelta(hours=20))
        assert _score(_candidate(2)) > _score(old)

    def test_a_story_carried_widely_scores_higher(self) -> None:
        broad = _candidate(1, sources=8, languages=3)
        assert _score(broad) > _score(_candidate(2))

    def test_closeness_to_the_readers_profile_counts(self) -> None:
        near = _candidate(1, similarity=0.6)
        far = _candidate(2, similarity=0.05)
        assert _score(near) > _score(far)

    def test_follows_count(self) -> None:
        signals = Signals(
            followed_topics=frozenset({"medtop:15000000"}),
            followed_sources=frozenset({7}),
            followed_stories=frozenset({99}),
        )
        plain = _score(_candidate(1), signals)
        assert _score(_candidate(2, topic_ids=frozenset({"medtop:15000000"})), signals) > plain
        assert _score(_candidate(3, source_id=7), signals) > plain
        assert _score(_candidate(4, story_cluster_id=99), signals) > plain

    def test_shown_and_passed_over_is_demoted(self) -> None:
        signals = Signals(fatigue={1: 3})
        assert _score(_candidate(1), signals) < _score(_candidate(2), signals)

    def test_already_opened_is_demoted(self) -> None:
        signals = Signals(seen=frozenset({1}))
        assert _score(_candidate(1), signals) < _score(_candidate(2), signals)

    def test_top_ignores_the_readers_profile(self) -> None:
        near = _candidate(1, similarity=0.9)
        far = _candidate(2, similarity=0.0)
        assert scoring.score(near, Signals(), scoring.TOP, now=NOW) == pytest.approx(
            scoring.score(far, Signals(), scoring.TOP, now=NOW)
        )


class TestLift:
    def test_no_data_is_no_lift(self) -> None:
        assert scoring.lift(0, 0, 1 / 17, strength=5) == pytest.approx(0.0)

    def test_evidence_moves_it_gradually(self) -> None:
        one = scoring.lift(1, 1, 1 / 17, strength=5)
        many = scoring.lift(20, 20, 1 / 17, strength=5)
        assert 0 < one < many <= scoring.LIFT_MAX

    def test_is_clipped(self) -> None:
        assert scoring.lift(0, 1000, 0.5, strength=5) == scoring.LIFT_MIN


class TestOnePerStory:
    def test_keeps_the_best_scored_report_of_each_story(self) -> None:
        candidates = [
            _candidate(1, story_cluster_id=10),
            _candidate(2, story_cluster_id=10),
            _candidate(3),
        ]
        assert scoring.one_per_story(candidates, [0.1, 0.9, 0.5]) == [1, 2]


class TestProfile:
    def test_needs_two_reads(self) -> None:
        vector = np.ones(4, dtype=np.float32)
        assert scoring.profile_vector([(vector, 1.0)]) is None

    def test_is_a_unit_weighted_mean(self) -> None:
        a = np.array([1, 0, 0, 0], dtype=np.float32)
        b = np.array([0, 1, 0, 0], dtype=np.float32)
        profile = scoring.profile_vector([(a, 3.0), (b, 1.0)])
        assert profile is not None
        assert float(np.linalg.norm(profile)) == pytest.approx(1.0)
        assert profile[0] > profile[1] > 0

    def test_not_interested_pulls_away(self) -> None:
        a = np.array([1, 0, 0, 0], dtype=np.float32)
        b = np.array([0, 1, 0, 0], dtype=np.float32)
        profile = scoring.profile_vector([(a, 1.0), (b, 1.0)], [b])
        assert profile is not None
        assert profile[0] > profile[1]


def _unit_rows(count: int, dimensions: int = 8, seed: int = 1) -> np.ndarray:
    rows = np.random.default_rng(seed).normal(size=(count, dimensions)).astype(np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


class TestArrange:
    def test_deterministic_is_the_argmax_with_propensity_one(self) -> None:
        relevance = np.array([0.2, 1.0, 0.5])
        placed = scoring.arrange(
            relevance,
            np.eye(3, dtype=np.float32),
            [1, 2, 3],
            count=3,
            mmr_lambda=1.0,
            sampling=scoring.DETERMINISTIC,
            rng=None,
        )
        assert [p.index for p in placed] == [1, 2, 0]
        assert all(p.propensity == 1.0 for p in placed)

    def test_redundancy_pushes_a_near_duplicate_down(self) -> None:
        # 0 and 1 point the same way; 2 is different but slightly less relevant.
        embeddings = np.array([[1, 0], [1, 0], [0, 1]], dtype=np.float32)
        placed = scoring.arrange(
            np.array([1.0, 0.95, 0.9]),
            embeddings,
            [1, 2, 3],
            count=3,
            mmr_lambda=0.7,
            sampling=scoring.DETERMINISTIC,
            rng=None,
        )
        assert [p.index for p in placed] == [0, 2, 1]

    def test_no_source_three_in_a_row_or_past_its_cap(self) -> None:
        size = 40
        sources = [1] * 30 + list(range(2, 12))  # one publisher dominates the pool
        placed = scoring.arrange(
            np.linspace(1.0, 0.5, size),
            np.zeros((size, 8), dtype=np.float32),
            sources,
            count=15,
            mmr_lambda=1.0,
            sampling=scoring.DETERMINISTIC,
            rng=None,
        )
        served = [sources[p.index] for p in placed]
        assert served.count(1) == Sampling().source_cap
        assert all(
            not (served[i] == served[i + 1] == served[i + 2] == 1) for i in range(len(served) - 2)
        )

    def test_sampling_logs_real_probabilities_and_repeats_with_its_seed(self) -> None:
        size = 60
        args = {
            "count": 30,
            "mmr_lambda": 0.7,
            "sampling": Sampling(),
        }
        relevance = np.linspace(1.0, 0.1, size)
        embeddings = _unit_rows(size)
        sources = list(range(size))
        first = scoring.arrange(
            relevance,
            embeddings,
            sources,
            rng=np.random.default_rng(42),
            **args,  # type: ignore[arg-type]
        )
        again = scoring.arrange(
            relevance,
            embeddings,
            sources,
            rng=np.random.default_rng(42),
            **args,  # type: ignore[arg-type]
        )
        assert [p.index for p in first] == [p.index for p in again]
        assert all(0 < p.propensity <= 1 for p in first)
        assert any(p.propensity < 1 for p in first)
        # Every one of the top candidates keeps at least epsilon's share.
        floor = Sampling().epsilon / Sampling().candidates
        assert min(p.propensity for p in first) >= floor - 1e-12

    def test_exploration_slots_draw_uniformly_from_what_is_explorable(self) -> None:
        size = 30
        explorable = np.zeros(size, dtype=bool)
        explorable[20:] = True
        placed = scoring.arrange(
            np.linspace(1.0, 0.1, size),
            _unit_rows(size),
            list(range(size)),
            count=24,
            mmr_lambda=0.7,
            sampling=Sampling(),
            rng=np.random.default_rng(3),
            explorable=explorable,
            exploration_every=12,
        )
        exploring = [(at, p) for at, p in enumerate(placed) if p.exploration]
        assert [at for at, _p in exploring] == [6, 18]
        assert all(explorable[p.index] for _at, p in exploring)
        # Uniform over the explorable stories still unplaced at that slot.
        before = sum(1 for p in placed[:6] if explorable[p.index])
        assert exploring[0][1].propensity == pytest.approx(1 / (10 - before))


def test_importance_matches_v1s_breadth_and_reach() -> None:
    candidate = _candidate(1, sources=4, languages=3)
    expected = math.log1p(0.5 * 2) + math.log1p(0.35 * 2)
    assert scoring.importance(candidate) == pytest.approx(expected)
