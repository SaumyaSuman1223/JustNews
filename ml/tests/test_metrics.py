"""The metrics, against numbers worked out by hand - not against the code
being reproduced (jnfinding/metrics.py says why)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from jnfinding import metrics

# Four candidates: positives at candidate 0 and 3. By score the order is
# 0 (+), 1 (-), 3 (+), 2 (-): positives at ranks 1 and 3.
LABELS = [1, 0, 0, 1]
SCORES = [0.9, 0.8, 0.1, 0.2]


def test_auc_counts_correctly_ordered_pairs() -> None:
    # Pairs (pos, neg): (0,1) yes, (0,2) yes, (3,1) no, (3,2) yes -> 3 of 4.
    assert metrics.auc(LABELS, SCORES) == pytest.approx(0.75)


def test_auc_counts_a_tie_as_half() -> None:
    assert metrics.auc([1, 0], [0.5, 0.5]) == pytest.approx(0.5)


def test_auc_is_undefined_without_both_classes() -> None:
    assert math.isnan(metrics.auc([1, 1], [0.1, 0.2]))
    assert math.isnan(metrics.auc([0, 0], [0.1, 0.2]))


def test_mrr_averages_reciprocal_ranks_over_positives() -> None:
    # (1/1 + 1/3) / 2
    assert metrics.mrr(LABELS, SCORES) == pytest.approx((1 + 1 / 3) / 2)


def test_ndcg_at_10() -> None:
    # DCG = 1/log2(2) + 1/log2(4) = 1.5; ideal = 1/log2(2) + 1/log2(3).
    ideal = 1 + 1 / math.log2(3)
    assert metrics.ndcg(LABELS, SCORES, 10) == pytest.approx(1.5 / ideal)


def test_ndcg_at_1_sees_only_the_top() -> None:
    assert metrics.ndcg(LABELS, SCORES, 1) == pytest.approx(1.0)
    assert metrics.ndcg([0, 1], [0.9, 0.1], 1) == pytest.approx(0.0)


def test_a_perfect_ranking_scores_one_everywhere() -> None:
    report = metrics.evaluate([([1, 0, 0], [3.0, 2.0, 1.0])])
    assert (report.auc, report.mrr, report.ndcg5, report.ndcg10) == (1.0, 1.0, 1.0, 1.0)


def test_evaluate_skips_impressions_that_say_nothing() -> None:
    report = metrics.evaluate([(LABELS, SCORES), ([0, 0], [0.1, 0.2])])
    assert report.impressions == 1
    assert report.auc == pytest.approx(0.75)


def test_ties_keep_candidate_order() -> None:
    # Equal scores: candidate order decides, so the positive listed first
    # ranks first.
    assert metrics.mrr([1, 0], [0.5, 0.5]) == pytest.approx(1.0)
    assert metrics.mrr([0, 1], [0.5, 0.5]) == pytest.approx(0.5)


def test_snips_reweights_logged_outcomes() -> None:
    rewards = np.array([1.0, 0.0, 1.0])
    logged = np.array([0.5, 0.25, 0.25])
    # A target that would always have made the first choice.
    target = np.array([1.0, 0.0, 0.0])
    assert metrics.snips(rewards, logged, target) == pytest.approx(1.0)
    # The logging policy evaluated on itself: its own average reward.
    assert metrics.snips(rewards, logged, logged) == pytest.approx(2 / 3)
