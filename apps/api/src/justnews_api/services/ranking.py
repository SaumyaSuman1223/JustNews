"""The Stage 5 heuristic ranker.

recency decay x topic affinity x popularity x source trust x language match,
with a penalty for already-seen. Pure arithmetic over rows the repository
layer already fetched - no model, no forward pass. ADR 0004's "no inference
in the hot path" is about a neural network's forward pass; it says nothing
about arithmetic on numbers already sitting in Postgres, which is all this
is. The learned ranker (Stage 6) replaces this function, not the request
path around it.

MMR (Maximal Marginal Relevance) then re-ranks the scored pool so the feed
does not collapse into one topic or one source even when that topic
legitimately scores highest for everyone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from justnews_api.repositories.content import ArticleRow

RECENCY_HALF_LIFE_HOURS = 18.0
SEEN_PENALTY = 0.15
FOLLOWED_TOPIC_BOOST = 1.6
POPULARITY_WEIGHT = 0.35
SOURCE_TRUST_FLOOR = 0.5  # a low-trust source is deprioritised, never zeroed out
MMR_LAMBDA = 0.7  # relevance vs diversity trade-off


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    article: ArticleRow
    score: float
    topic_ids: frozenset[str]


def _recency_score(published_at: datetime, *, now: datetime) -> float:
    age_hours = max((now - published_at).total_seconds() / 3600.0, 0.0)
    # float(...): float.__pow__'s stub returns Any (a negative base with a
    # fractional exponent can produce a complex number), which would
    # otherwise leak Any out of a function declared to return float.
    return float(0.5 ** (age_hours / RECENCY_HALF_LIFE_HOURS))


def _language_score(language: str, preferred_languages: list[str]) -> float:
    """1.0 for the reader's first-listed language, tapering for later ones -
    within an already language-filtered candidate pool, this is what makes a
    reader who lists ["en", "es"] see mostly English rather than a coin
    flip between the two."""
    if not preferred_languages:
        return 1.0
    try:
        rank = preferred_languages.index(language)
    except ValueError:
        return 0.7  # candidates are pre-filtered to these languages; a defensive fallback
    return max(1.0 - 0.15 * rank, 0.6)


def score_candidates(
    candidates: list[ArticleRow],
    *,
    topic_ids_by_article: dict[int, list[str]],
    click_counts: dict[int, int],
    followed_topic_ids: set[str],
    seen_article_ids: set[int],
    preferred_languages: list[str],
    now: datetime | None = None,
) -> list[ScoredCandidate]:
    now = now or datetime.now(UTC)
    scored: list[ScoredCandidate] = []
    for article in candidates:
        topic_ids = frozenset(topic_ids_by_article.get(article.id, ()))
        recency = _recency_score(article.published_at, now=now)
        affinity = FOLLOWED_TOPIC_BOOST if topic_ids & followed_topic_ids else 1.0
        popularity = 1.0 + POPULARITY_WEIGHT * math.log1p(click_counts.get(article.id, 0))
        trust = SOURCE_TRUST_FLOOR + (1 - SOURCE_TRUST_FLOOR) * article.source_trust_score
        language = _language_score(article.language, preferred_languages)

        score = recency * affinity * popularity * trust * language
        if article.id in seen_article_ids:
            score *= SEEN_PENALTY

        scored.append(ScoredCandidate(article=article, score=score, topic_ids=topic_ids))
    return scored


def dedupe_story_clusters(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Keep only the highest-scored article per story cluster - the ranker's
    own "don't show the same story twice" rule, downstream of and distinct
    from the ingestion-time dedup that built the clusters in the first
    place."""
    best_by_cluster: dict[int, ScoredCandidate] = {}
    standalone: list[ScoredCandidate] = []
    for candidate in candidates:
        cluster_id = candidate.article.story_cluster_id
        if cluster_id is None:
            standalone.append(candidate)
            continue
        current = best_by_cluster.get(cluster_id)
        if current is None or candidate.score > current.score:
            best_by_cluster[cluster_id] = candidate
    return standalone + list(best_by_cluster.values())


def _similarity(a: ScoredCandidate, b: ScoredCandidate) -> float:
    same_source = a.article.source_slug == b.article.source_slug
    shared_topic = bool(a.topic_ids & b.topic_ids)
    if shared_topic and same_source:
        return 1.0
    if shared_topic:
        return 0.6
    if same_source:
        return 0.3
    return 0.0


def diversify(candidates: list[ScoredCandidate]) -> list[ArticleRow]:
    """Greedy MMR over the whole scored pool, not just one page of it - the
    feed service slices pages out of this result, so the ordering has to be
    stable and complete across however many pages a reader scrolls.

    Repeatedly takes the candidate that trades relevance against redundancy
    with what has already been selected, rather than a flat sort by score -
    a flat sort is exactly how a feed collapses into eight cards about the
    same story from the highest-trust source.
    """
    pool = sorted(candidates, key=lambda c: c.score, reverse=True)
    if not pool:
        return []
    selected = [pool.pop(0)]
    while pool:
        best_index = 0
        best_mmr = float("-inf")
        for index, candidate in enumerate(pool):
            redundancy = max(_similarity(candidate, chosen) for chosen in selected)
            mmr = MMR_LAMBDA * candidate.score - (1 - MMR_LAMBDA) * redundancy
            if mmr > best_mmr:
                best_mmr = mmr
                best_index = index
        selected.append(pool.pop(best_index))
    return [candidate.article for candidate in selected]
