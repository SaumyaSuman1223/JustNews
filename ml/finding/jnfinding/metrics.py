"""The metrics every ranker here is judged by - ours, not borrowed.

Per impression (one reader, one set of shown candidates with 0/1 labels):
AUC, MRR, nDCG@5 and nDCG@10, the four the FINDING paper and MIND report,
then averaged over impressions. Defined exactly as the MIND evaluation
script defines them, so numbers are comparable with the paper's; written
independently of it and tested against hand calculations
(ml/tests/test_metrics.py), because a reproduction judged by the code it
reproduces proves nothing.

Ties are broken by candidate order (a stable sort), stated rather than left
to whatever a reversed argsort happens to do.

For the offline replay of logged JustNews traffic there are also the
inverse-propensity estimators, over the probabilities the serving ranker
logged with every placement (ADR 0015).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


def _order(scores: Sequence[float]) -> npt.NDArray[np.int64]:
    """Candidate indexes by score, highest first; ties keep candidate order."""
    return np.argsort(-np.asarray(scores, dtype=np.float64), kind="stable")


def auc(labels: Sequence[int], scores: Sequence[float]) -> float:
    """The probability a random positive outscores a random negative, ties
    counting half (the Mann-Whitney statistic; equal to ROC AUC). NaN when
    the impression has no positive or no negative."""
    y = np.asarray(labels, dtype=np.float64)
    s = np.asarray(scores, dtype=np.float64)
    positives, negatives = s[y > 0], s[y <= 0]
    if len(positives) == 0 or len(negatives) == 0:
        return math.nan
    greater = (positives[:, None] > negatives[None, :]).sum()
    ties = (positives[:, None] == negatives[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(positives) * len(negatives)))


def mrr(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Mean reciprocal rank over the positives, as MIND defines it: the sum
    of 1/rank for every positive, divided by the number of positives."""
    y = np.asarray(labels, dtype=np.float64)[_order(scores)]
    if y.sum() == 0:
        return math.nan
    ranks = np.arange(1, len(y) + 1)
    return float((y / ranks).sum() / y.sum())


def dcg(labels: Sequence[int], scores: Sequence[float], k: int) -> float:
    y = np.asarray(labels, dtype=np.float64)[_order(scores)][:k]
    gains = 2.0**y - 1.0
    discounts = np.log2(np.arange(len(y)) + 2.0)
    return float((gains / discounts).sum())


def ndcg(labels: Sequence[int], scores: Sequence[float], k: int) -> float:
    ideal = dcg(labels, labels, k)
    if ideal == 0:
        return math.nan
    return dcg(labels, scores, k) / ideal


@dataclass(frozen=True, slots=True)
class Report:
    auc: float
    mrr: float
    ndcg5: float
    ndcg10: float
    impressions: int

    def as_dict(self) -> dict[str, float]:
        return {
            "AUC": self.auc,
            "MRR": self.mrr,
            "nDCG@5": self.ndcg5,
            "nDCG@10": self.ndcg10,
            "impressions": float(self.impressions),
        }


def evaluate(impressions: Sequence[tuple[Sequence[int], Sequence[float]]]) -> Report:
    """Each metric averaged over the impressions where it is defined - one
    with no positive, or (for AUC) no negative, says nothing and is skipped,
    as MIND's script skips it."""
    rows = [(auc(y, s), mrr(y, s), ndcg(y, s, 5), ndcg(y, s, 10)) for y, s in impressions]
    usable = [row for row in rows if not math.isnan(row[0])]
    if not usable:
        return Report(math.nan, math.nan, math.nan, math.nan, 0)
    table = np.array(usable, dtype=np.float64)
    means = table.mean(axis=0)
    return Report(
        auc=float(means[0]),
        mrr=float(means[1]),
        ndcg5=float(means[2]),
        ndcg10=float(means[3]),
        impressions=len(usable),
    )


def snips(rewards: Array, logged: Array, target: Array) -> float:
    """Self-normalised inverse propensity estimate of the reward a target
    policy would have earned on logged traffic: each logged outcome weighted
    by target probability / logging probability, divided by the sum of the
    weights. Unbiased-in-the-limit and far lower variance than plain IPS at
    the sample sizes a beta produces. Needs `logged` > 0 wherever `target`
    is - the support the sampled serving order exists to provide."""
    weights = np.asarray(target, dtype=np.float64) / np.asarray(logged, dtype=np.float64)
    total = weights.sum()
    if total == 0:
        return math.nan
    return float((weights * np.asarray(rewards, dtype=np.float64)).sum() / total)
