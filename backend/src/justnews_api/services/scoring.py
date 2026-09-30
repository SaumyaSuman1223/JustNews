"""Ranker v2's arithmetic (ADR 0015): a score per candidate, one article per
story, and the diversified, sampled order that is served - with the
probability each placement had, which is what makes a later ranker
comparable offline against this one.

No model and no forward pass (ADR 0004). Every term is arithmetic on numbers
already stored: a cosine between two stored vectors is a dot product, the
same kind of thing as v1's recency decay. Pure functions over plain values,
so tests need no database and an offline replay can recompute what was
served from the logs.

Scores are log-linear - each term adds to a log score, so each multiplies
the relevance - which keeps every term readable on its own: a followed
source's `log(1.4)` is "40% more likely to lead", whatever else is true.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import numpy as np
import numpy.typing as npt

Vector = npt.NDArray[np.float32]

#: As in v1 (services/ranking.py): what a story gains per doubling of the
#: outlets carrying it, and per extra language it is reported in.
BREADTH_WEIGHT = 0.5
LANGUAGE_WEIGHT = 0.35
#: A low-trust source is deprioritised, never zeroed out.
TRUST_FLOOR = 0.5
#: Lifts are clipped: one reader's handful of clicks is evidence, not proof,
#: and no single topic or source should be able to swamp every other term.
LIFT_MIN, LIFT_MAX = -1.0, 1.5
#: A profile needs this many positive reads before it says anything.
MIN_PROFILE_ITEMS = 2
#: How much a "not interested" pulls the profile away from what it marked.
NEGATIVE_WEIGHT = 0.5
#: Two cards from one publisher are this redundant even on different events.
SAME_SOURCE_SIMILARITY = 0.3


@dataclass(frozen=True, slots=True)
class RankReason:
    """Why a card is on the reader's feed, in the one term that actually moved
    it (design-system.md: "every ranked card can explain itself"). Only a
    factor the ranker really applied; a card placed on recency and language
    alone carries no reason rather than an invented one."""

    kind: Literal[
        "followed_topic",
        "followed_source",
        "followed_story",
        "similar",
        "trending",
        "exploration",
    ]
    topic_id: str | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    article_id: int
    source_id: int
    story_cluster_id: int | None
    language: str
    published_at: datetime
    trust: float
    #: Outlets and languages carrying its story; 1 and 1 when unclustered.
    sources: int
    languages: int
    topic_ids: frozenset[str]
    #: Cosine to the reader's profile vector; None when there is no profile.
    similarity: float | None = None


@dataclass(frozen=True, slots=True)
class Weights:
    """One surface's balance of terms. The same function scores every surface;
    what differs is how much each term counts."""

    half_life_hours: float
    importance: float
    similarity: float
    topic: float
    source: float
    followed_topic: float
    followed_source: float
    followed_story: float
    fatigue: float
    #: Added for an article the reader already opened (a log multiplier).
    seen: float
    popularity: float
    mmr_lambda: float
    #: An exploration slot every this many positions, or never.
    exploration_every: int | None = None


#: For You: the reader's own reading leads.
FOR_YOU = Weights(
    half_life_hours=18.0,
    importance=1.0,
    similarity=3.0,
    topic=0.6,
    source=0.3,
    followed_topic=math.log(2.0),
    followed_source=math.log(1.4),
    followed_story=math.log(2.0),
    fatigue=0.6,
    seen=math.log(0.15),
    popularity=0.3,
    mmr_lambda=0.7,
    exploration_every=12,
)
#: Top: what matters now, for everyone - importance leads, reading barely
#: counts, and more diversity than a personal feed.
TOP = Weights(
    half_life_hours=12.0,
    importance=1.5,
    similarity=0.0,
    topic=0.0,
    source=0.0,
    followed_topic=0.0,
    followed_source=0.0,
    followed_story=0.0,
    fatigue=0.3,
    seen=math.log(0.3),
    popularity=0.3,
    mmr_lambda=0.6,
)
#: A topic: a longer window, since a topic moves slower than the front page.
TOPIC = Weights(
    half_life_hours=36.0,
    importance=1.0,
    similarity=1.0,
    topic=0.0,
    source=0.2,
    followed_topic=0.0,
    followed_source=math.log(1.4),
    followed_story=math.log(2.0),
    fatigue=0.5,
    seen=math.log(0.2),
    popularity=0.3,
    mmr_lambda=0.7,
)


@dataclass(frozen=True, slots=True)
class Signals:
    """What is known about the reader, as of the feed's window. Empty for a
    reader nothing is known about - every term then contributes nothing and
    the score is the non-personal importance order."""

    languages: tuple[str, ...] = ()
    topic_lift: dict[str, float] = field(default_factory=dict)
    source_lift: dict[int, float] = field(default_factory=dict)
    followed_topics: frozenset[str] = frozenset()
    followed_sources: frozenset[int] = frozenset()
    followed_stories: frozenset[int] = frozenset()
    #: Times each article was shown to this reader and not opened.
    fatigue: dict[int, int] = field(default_factory=dict)
    #: Articles the reader opened recently.
    seen: frozenset[int] = frozenset()
    #: Recent click-through lift per article, across readers.
    popularity: dict[int, float] = field(default_factory=dict)


def language_score(language: str, preferred: Sequence[str]) -> float:
    """1.0 for the reader's first language, tapering for later ones - as v1."""
    if not preferred:
        return 1.0
    try:
        rank = list(preferred).index(language)
    except ValueError:
        return 0.7
    return max(1.0 - 0.15 * rank, 0.6)


def lift(count: float, total: float, prior_share: float, *, strength: float) -> float:
    """How much more than the prior a share is, in log terms, with a prior
    worth `strength` observations: `log(((n + k·q) / (N + k)) / q)`. With no
    data it is 0; one click moves it a little, twenty a lot."""
    if prior_share <= 0:
        return 0.0
    smoothed = (count + strength * prior_share) / (total + strength)
    return min(max(math.log(smoothed / prior_share), LIFT_MIN), LIFT_MAX)


def importance(candidate: Candidate) -> float:
    """Breadth and reach, in log terms: how widely the story is carried."""
    breadth = math.log1p(BREADTH_WEIGHT * math.log2(max(candidate.sources, 1)))
    reach = math.log1p(LANGUAGE_WEIGHT * (max(candidate.languages, 1) - 1))
    return breadth + reach


def base_score(candidate: Candidate, weights: Weights, *, now: datetime) -> float:
    """The non-personal part: recency, importance and trust."""
    age_hours = max((now - candidate.published_at).total_seconds() / 3600.0, 0.0)
    recency = -math.log(2.0) * age_hours / weights.half_life_hours
    trust = math.log(TRUST_FLOOR + (1.0 - TRUST_FLOOR) * candidate.trust)
    return recency + weights.importance * importance(candidate) + trust


def score(candidate: Candidate, signals: Signals, weights: Weights, *, now: datetime) -> float:
    total = base_score(candidate, weights, now=now)
    total += math.log(language_score(candidate.language, signals.languages))
    if candidate.similarity is not None:
        total += weights.similarity * candidate.similarity
    if candidate.topic_ids:
        total += weights.topic * max(signals.topic_lift.get(t, 0.0) for t in candidate.topic_ids)
        if candidate.topic_ids & signals.followed_topics:
            total += weights.followed_topic
    total += weights.source * signals.source_lift.get(candidate.source_id, 0.0)
    if candidate.source_id in signals.followed_sources:
        total += weights.followed_source
    if candidate.story_cluster_id is not None and (
        candidate.story_cluster_id in signals.followed_stories
    ):
        total += weights.followed_story
    total -= weights.fatigue * math.log1p(signals.fatigue.get(candidate.article_id, 0))
    if candidate.article_id in signals.seen:
        total += weights.seen
    total += weights.popularity * signals.popularity.get(candidate.article_id, 0.0)
    return total


def one_per_story(candidates: Sequence[Candidate], scores: Sequence[float]) -> list[int]:
    """Indexes of the best-scored article per story, plus every unclustered
    one - the reader's own language wins a story through its language term."""
    best: dict[int, int] = {}
    kept: list[int] = []
    for index, candidate in enumerate(candidates):
        cluster = candidate.story_cluster_id
        if cluster is None:
            kept.append(index)
        elif cluster not in best or scores[index] > scores[best[cluster]]:
            best[cluster] = index
    return sorted(kept + list(best.values()))


def profile_vector(
    positives: Sequence[tuple[Vector, float]], negatives: Sequence[Vector] = ()
) -> Vector | None:
    """The reader's reading as one direction in the shared vector space: a
    weighted mean of what they opened, saved and shared, pushed away from
    what they marked not interesting, unit length. None below
    MIN_PROFILE_ITEMS - two reads are the least that say anything."""
    usable = [(vector, weight) for vector, weight in positives if weight > 0]
    if len(usable) < MIN_PROFILE_ITEMS:
        return None
    stacked = np.stack([vector for vector, _ in usable]).astype(np.float32)
    weights = np.array([weight for _, weight in usable], dtype=np.float32)
    mean = (stacked * weights[:, None]).sum(axis=0) / weights.sum()
    if negatives:
        mean = mean - NEGATIVE_WEIGHT * np.stack(list(negatives)).astype(np.float32).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm == 0.0:
        return None
    result: Vector = (mean / norm).astype(np.float32)
    return result


@dataclass(frozen=True, slots=True)
class Sampling:
    """How a served order is drawn. `temperature` 0 is deterministic - the
    argmax at every step, as for a reader whose feed is not logged, where
    randomness would buy nothing - otherwise each step samples from the
    top `candidates` by MMR value, mixing in `epsilon` of uniform so every
    one of them keeps a real chance (the support an offline estimator
    needs)."""

    temperature: float = 0.05
    epsilon: float = 0.05
    candidates: int = 20
    #: At most this many cards from one source in any `source_window` in a
    #: row, and never three in a row, unless nothing else is left.
    source_cap: int = 5
    source_window: int = 24


DETERMINISTIC = Sampling(temperature=0.0, epsilon=0.0)


def language_share(reading: int) -> float | None:
    """The most of any window one language may take, for a reader of
    `reading` languages - None for one. A constant penalty on a second
    language does not make a mix when the first has stories to spare: at
    0.85 an English and Hindi reader's Top was 47 English of 50. A share
    guarantees the languages they chose each get a real part of the page."""
    if reading < 2:
        return None
    return 0.7 if reading == 2 else 0.6


@dataclass(frozen=True, slots=True)
class Placement:
    #: Into the candidate list given to `arrange`.
    index: int
    #: The probability this card had of being chosen at this position, given
    #: the positions before it - the product over a page's first k positions
    #: is the probability of that prefix, which slate estimators need.
    propensity: float
    exploration: bool = False


def arrange(
    relevance: npt.NDArray[np.float64],
    embeddings: npt.NDArray[np.float32],
    source_ids: Sequence[int],
    *,
    count: int,
    mmr_lambda: float,
    sampling: Sampling,
    rng: np.random.Generator | None,
    explorable: npt.NDArray[np.bool_] | None = None,
    exploration_every: int | None = None,
    languages: Sequence[str] | None = None,
    max_language_share: float | None = None,
) -> list[Placement]:
    """The served order: greedy MMR - relevance traded against redundancy
    with what is already placed - sampled step by step when `rng` is given.

    `relevance` is exp(score - max score), in (0, 1]. `embeddings` are unit
    rows (a zero row for an article with none: it is then redundant only by
    source). Redundancy is the maximum similarity to anything placed so far,
    kept as a running value and updated against the newly placed card only.

    Exploration slots (`exploration_every`, For You only) draw uniformly from
    `explorable` - stories outside what the reader already reads - at a
    fixed position in every run of that many, so exploration is spread
    through the feed rather than parked at its end, and its propensity is
    exactly 1 / how many were eligible.

    With `max_language_share`, no one of `languages` (each candidate's) takes
    more than that share of any `source_window` in a row. The rules relax in
    order - the language share first, then the source rule - only when
    nothing else is left.
    """
    size = len(source_ids)
    if size == 0 or count <= 0:
        return []
    sources = np.asarray(source_ids)
    tongues = np.asarray(languages) if languages is not None else None
    language_cap = (
        math.ceil(max_language_share * sampling.source_window)
        if max_language_share is not None and tongues is not None
        else None
    )
    remaining = np.ones(size, dtype=bool)
    redundancy = np.zeros(size, dtype=np.float64)
    placed: list[Placement] = []
    stochastic = rng is not None and sampling.temperature > 0

    for position in range(min(count, size)):
        by_source = remaining & _source_allows(placed, sources, sampling)
        eligible = by_source
        if language_cap is not None and tongues is not None:
            eligible = by_source & _language_allows(placed, tongues, language_cap, sampling)
            if not eligible.any():
                eligible = by_source
        if not eligible.any():
            eligible = remaining.copy()

        exploring = (
            rng is not None
            and explorable is not None
            and exploration_every is not None
            and position % exploration_every == exploration_every // 2
            and bool((eligible & explorable).any())
        )
        if exploring and rng is not None and explorable is not None:
            pool = np.flatnonzero(eligible & explorable)
            chosen = int(pool[int(rng.integers(len(pool)))])
            placement = Placement(index=chosen, propensity=1.0 / len(pool), exploration=True)
        else:
            value = mmr_lambda * relevance - (1.0 - mmr_lambda) * redundancy
            indexes = np.flatnonzero(eligible)
            ordered = indexes[np.argsort(-value[indexes], kind="stable")]
            if not stochastic or rng is None:
                placement = Placement(index=int(ordered[0]), propensity=1.0)
            else:
                top = ordered[: sampling.candidates]
                logits = (value[top] - value[top[0]]) / sampling.temperature
                weights = np.exp(logits)
                probabilities = (1.0 - sampling.epsilon) * weights / weights.sum()
                probabilities += sampling.epsilon / len(top)
                pick = int(rng.choice(len(top), p=probabilities))
                placement = Placement(index=int(top[pick]), propensity=float(probabilities[pick]))

        placed.append(placement)
        remaining[placement.index] = False
        similar = embeddings @ embeddings[placement.index]
        same_source = np.where(sources == sources[placement.index], SAME_SOURCE_SIMILARITY, 0.0)
        redundancy = np.maximum(redundancy, np.maximum(similar.astype(np.float64), same_source))
    return placed


def _source_allows(
    placed: list[Placement], sources: npt.NDArray[np.int_], sampling: Sampling
) -> npt.NDArray[np.bool_]:
    """Which candidates the per-source rule still allows at the next position."""
    allowed = np.ones(len(sources), dtype=bool)
    window = [sources[p.index] for p in placed[-(sampling.source_window - 1) :]]
    for source in set(window):
        if window.count(source) >= sampling.source_cap:
            allowed &= sources != source
    if len(placed) >= 2 and sources[placed[-1].index] == sources[placed[-2].index]:
        allowed &= sources != sources[placed[-1].index]
    return allowed


def _language_allows(
    placed: list[Placement], languages: npt.NDArray[np.str_], cap: int, sampling: Sampling
) -> npt.NDArray[np.bool_]:
    """Which candidates the language share still allows at the next position."""
    allowed = np.ones(len(languages), dtype=bool)
    window = [languages[p.index] for p in placed[-(sampling.source_window - 1) :]]
    for language in set(window):
        if window.count(language) >= cap:
            allowed &= languages != language
    return allowed
