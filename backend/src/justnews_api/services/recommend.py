"""Ranker v2 (ADR 0015): one ranker for For You, Top and a topic, for every
reader - signed in, signed out, or not logged at all.

The pipeline, per page request:

1. **The reader, as of the feed's window.** Opens, shares and saves (or,
   signed out, the device's own recent reads) become a profile vector and
   topic and source lifts; follows, recent opens, "not interested" and how
   often each article was shown unopened are read as of the same moment.
2. **Candidates.** A time window (not a count) with a per-source quota; the
   articles nearest the profile; new reports on followed stories.
3. **Score, one article per story, arrange.** services/scoring.py - a
   sampled MMR when the page is logged, so every placement has a real
   probability; deterministic when it is not.
4. **The page.** Full rows only for the cards served.

No model runs here (ADR 0004): the vectors were computed at ingest, and
everything below is arithmetic on them.
"""

from __future__ import annotations

import secrets
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import numpy as np
import numpy.typing as npt
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import ranking as ranking_repo
from justnews_api.repositories import recommend as repo
from justnews_api.services import scoring
from justnews_api.services.cursor import (
    MAX_CURSOR_HISTORY,
    FeedCursor,
    decode_feed_cursor,
    encode_feed_cursor,
)
from justnews_api.services.scoring import Candidate, RankReason, Signals

View = Literal["for_you", "top", "topic"]

POLICY = "heuristic_v2"

WEIGHTS: dict[View, scoring.Weights] = {
    "for_you": scoring.FOR_YOU,
    "top": scoring.TOP,
    "topic": scoring.TOPIC,
}
#: How far back each view's pool reaches - by time, never by count.
WINDOW: dict[View, timedelta] = {
    "for_you": timedelta(hours=36),
    "top": timedelta(hours=36),
    "topic": timedelta(days=7),
}
#: How far back the articles nearest the reader's profile may come from.
NEAREST_WINDOW = timedelta(hours=72)
NEAREST_LIMIT = 150
PER_SOURCE = 40
POOL_LIMIT = 1200
#: MMR runs over this many best-scored stories; the feed ends after them.
ARRANGE_POOL = 300
#: Exploration draws from this many of the pool's most important stories.
EXPLORE_POOL = 150

POSITIVE_LIMIT = 100
POSITIVE_WEIGHTS = {"click": 1.0, "share": 2.0, "save": 2.0}
POSITIVE_HALF_LIFE_DAYS = 7.0
#: Signed out there are no timestamps - the device's list is newest first.
HISTORY_DECAY = 0.9
NEGATIVE_LIMIT = 20

FATIGUE_WINDOW = timedelta(hours=72)
SEEN_WINDOW = timedelta(days=14)
POPULARITY_WINDOW = timedelta(days=7)

TOPIC_PRIOR_SHARE = 1 / 17  # IPTC's seventeen top-level topics
SOURCE_PRIOR_SHARE = 1 / 20
PRIOR_STRENGTH = 5.0
BASE_CTR = 0.05
CTR_PRIOR_STRENGTH = 20.0

TRENDING_MIN_CLICKS = 3
SIMILAR_REASON_MIN = 0.35


@dataclass(frozen=True, slots=True)
class RankRequest:
    view: View
    languages: list[str]
    #: The topic view's filter.
    topic_ids: list[str] | None = None
    #: Signed-out topic picks ("Make it yours"), weighed as follows.
    interests: list[str] = field(default_factory=list)
    user_id: UUID | None = None
    #: The browsing session - only present with analytics consent.
    session_id: str | None = None
    #: Signed out: recently opened article ids from this device, newest first.
    history: list[int] = field(default_factory=list)
    cursor: str | None = None
    page_size: int = 20
    #: Sample the order (and so log real propensities). Only worth it when
    #: the page is logged; otherwise the argmax, which is cacheable.
    stochastic: bool = False


@dataclass(frozen=True, slots=True)
class RankedItem:
    article: content_repo.ArticleRow
    position: int
    propensity: float
    reason: RankReason | None


@dataclass(frozen=True, slots=True)
class RankedPage:
    items: list[RankedItem]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class _Reader:
    signals: Signals
    profile: scoring.Vector | None
    excluded: set[int]


# Article vectors never change (the encoder is frozen - ADR 0005), so one
# fetched is good for the life of the process. Bounded: 20,000 vectors is
# about 30 MB, and the arrange pool is 300 of them.
_VECTORS: OrderedDict[int, tuple[int, scoring.Vector | None]] = OrderedDict()
_VECTOR_CACHE_SIZE = 20_000


async def _vectors(
    session: AsyncSession, article_ids: Sequence[int]
) -> dict[int, tuple[int, scoring.Vector | None]]:
    """Each article's source and unit vector, from the process cache first."""
    missing = [i for i in article_ids if i not in _VECTORS]
    if missing:
        for article_id, (source_id, vector) in (
            await repo.articles_with_embeddings(session, missing)
        ).items():
            if vector is not None:
                norm = float(np.linalg.norm(vector))
                vector = (vector / norm).astype(np.float32) if norm > 0 else None
            _VECTORS[article_id] = (source_id, vector)
            if len(_VECTORS) > _VECTOR_CACHE_SIZE:
                _VECTORS.popitem(last=False)
    found: dict[int, tuple[int, scoring.Vector | None]] = {}
    for article_id in article_ids:
        if article_id in _VECTORS:
            _VECTORS.move_to_end(article_id)
            found[article_id] = _VECTORS[article_id]
    return found


async def rank(session: AsyncSession, request: RankRequest) -> RankedPage:
    if request.cursor:
        cursor = decode_feed_cursor(request.cursor)
    else:
        cursor = FeedCursor(
            as_of=datetime.now(UTC),
            offset=0,
            seed=secrets.randbits(62) if request.stochastic else 0,
            history=tuple(request.history[:MAX_CURSOR_HISTORY]) if request.user_id is None else (),
        )
    weights = WEIGHTS[request.view]
    reader = await _reader(session, request, cursor)
    candidates = await _candidates(session, request, reader, cursor.as_of)
    if not candidates:
        return RankedPage(items=[], next_cursor=None)

    popularity = await repo.views_and_clicks(
        session,
        [c.article_id for c in candidates],
        since=cursor.as_of - POPULARITY_WINDOW,
        until=cursor.as_of,
    )
    signals = _with_popularity(reader.signals, popularity)
    clicks = {article_id: opened for article_id, (_seen, opened) in popularity.items()}

    scores = [scoring.score(c, signals, weights, now=cursor.as_of) for c in candidates]
    kept = scoring.one_per_story(candidates, scores)
    kept.sort(key=lambda index: (-scores[index], index))
    pool = kept[:ARRANGE_POOL]
    pooled = [candidates[i] for i in pool]
    pool_scores = np.array([scores[i] for i in pool], dtype=np.float64)

    vectors = await _vectors(session, [c.article_id for c in pooled])
    dimensions = next((v.shape[0] for _s, v in vectors.values() if v is not None), 1)
    matrix = np.zeros((len(pooled), dimensions), dtype=np.float32)
    for row, candidate in enumerate(pooled):
        vector = vectors.get(candidate.article_id, (0, None))[1]
        if vector is not None and vector.shape[0] == dimensions:
            matrix[row] = vector

    explorable = (
        _explorable(pooled, signals, weights, cursor.as_of)
        if weights.exploration_every is not None
        else None
    )
    rng = np.random.default_rng(cursor.seed) if request.stochastic else None
    wanted = cursor.offset + request.page_size
    placements = scoring.arrange(
        np.exp(pool_scores - pool_scores.max()),
        matrix,
        [c.source_id for c in pooled],
        count=wanted + 1,
        mmr_lambda=weights.mmr_lambda,
        sampling=scoring.Sampling() if request.stochastic else scoring.DETERMINISTIC,
        rng=rng,
        explorable=explorable,
        exploration_every=weights.exploration_every,
        languages=[c.language for c in pooled],
        max_language_share=scoring.language_share(len(request.languages)),
    )
    page = list(enumerate(placements))[cursor.offset : wanted]
    has_more = len(placements) > wanted

    # Marked not interesting since this feed was ranked: gone from the page
    # without re-ranking under the reader, so later pages stay the same cut.
    if request.user_id is not None:
        now_excluded = await repo.not_interested_ids(session, request.user_id)
        page = [(at, p) for at, p in page if pooled[p.index].article_id not in now_excluded]

    rows = await content_repo.get_articles_by_id(
        session, [pooled[p.index].article_id for _at, p in page]
    )
    served = [(at, p) for at, p in page if pooled[p.index].article_id in rows]
    articles = await content_repo.attach_outlets(
        session, [rows[pooled[p.index].article_id] for _at, p in served]
    )
    items = [
        RankedItem(
            article=article,
            position=at,
            propensity=p.propensity,
            reason=(
                _reason(pooled[p.index], p, signals, clicks) if request.view == "for_you" else None
            ),
        )
        for article, (at, p) in zip(articles, served, strict=True)
    ]
    next_cursor = (
        encode_feed_cursor(
            FeedCursor(as_of=cursor.as_of, offset=wanted, seed=cursor.seed, history=cursor.history)
        )
        if has_more
        else None
    )
    return RankedPage(items=items, next_cursor=next_cursor)


async def _reader(session: AsyncSession, request: RankRequest, cursor: FeedCursor) -> _Reader:
    """Everything known about the reader, as of the feed's window."""
    as_of = cursor.as_of
    positives: list[tuple[int, float]] = []
    negatives: list[int] = []
    excluded: set[int] = set()
    followed = repo.Follows(
        topics=frozenset(request.interests), sources=frozenset(), stories=frozenset()
    )
    seen: set[int] = set()
    if request.user_id is not None:
        for positive in await repo.recent_positives(
            session, request.user_id, until=as_of, limit=POSITIVE_LIMIT
        ):
            age_days = max((as_of - positive.at).total_seconds() / 86400.0, 0.0)
            decay = 0.5 ** (age_days / POSITIVE_HALF_LIFE_DAYS)
            positives.append((positive.article_id, POSITIVE_WEIGHTS[positive.kind] * decay))
        excluded = await repo.not_interested_ids(session, request.user_id, until=as_of)
        negatives = sorted(excluded)[-NEGATIVE_LIMIT:]
        account = await repo.follows(session, request.user_id)
        followed = repo.Follows(
            topics=account.topics | frozenset(request.interests),
            sources=account.sources,
            stories=account.stories,
        )
        seen = await repo.opened_ids(
            session, request.user_id, since=as_of - SEEN_WINDOW, until=as_of
        )
    else:
        positives = [
            (article_id, HISTORY_DECAY**rank) for rank, article_id in enumerate(cursor.history)
        ]
        seen = set(cursor.history)

    vectors = await _vectors(session, [a for a, _w in positives] + negatives)
    positive_vectors: list[tuple[scoring.Vector, float]] = []
    for article_id, weight in positives:
        vector = vectors.get(article_id, (0, None))[1]
        if vector is not None:
            positive_vectors.append((vector, weight))
    negative_vectors = [
        vector for a in negatives if (vector := vectors.get(a, (0, None))[1]) is not None
    ]
    profile = scoring.profile_vector(positive_vectors, negative_vectors)

    topics = await ranking_repo.topic_ids_by_article(session, [a for a, _w in positives])
    total = sum(w for _a, w in positives)
    topic_weight: dict[str, float] = {}
    source_weight: dict[int, float] = {}
    for article_id, weight in positives:
        for topic_id in topics.get(article_id, ()):
            topic_weight[topic_id] = topic_weight.get(topic_id, 0.0) + weight
        if article_id in vectors:
            source_id = vectors[article_id][0]
            source_weight[source_id] = source_weight.get(source_id, 0.0) + weight

    fatigue = await repo.unopened_shows(
        session,
        user_id=request.user_id,
        session_id=request.session_id,
        since=as_of - FATIGUE_WINDOW,
        until=as_of,
    )
    signals = Signals(
        languages=tuple(request.languages),
        topic_lift={
            t: scoring.lift(n, total, TOPIC_PRIOR_SHARE, strength=PRIOR_STRENGTH)
            for t, n in topic_weight.items()
        },
        source_lift={
            s: scoring.lift(n, total, SOURCE_PRIOR_SHARE, strength=PRIOR_STRENGTH)
            for s, n in source_weight.items()
        },
        followed_topics=followed.topics,
        followed_sources=followed.sources,
        followed_stories=followed.stories,
        fatigue=fatigue,
        seen=frozenset(seen),
    )
    return _Reader(signals=signals, profile=profile, excluded=excluded)


async def _candidates(
    session: AsyncSession, request: RankRequest, reader: _Reader, as_of: datetime
) -> list[Candidate]:
    weights = WEIGHTS[request.view]
    profile = (
        [float(x) for x in reader.profile]
        if reader.profile is not None and weights.similarity > 0
        else None
    )
    rows = await repo.window_candidates(
        session,
        languages=request.languages,
        since=as_of - WINDOW[request.view],
        until=as_of,
        per_source=PER_SOURCE,
        limit=POOL_LIMIT,
        topic_ids=request.topic_ids if request.view == "topic" else None,
        profile=profile,
    )
    if profile is not None and request.view == "for_you":
        rows += await repo.nearest_candidates(
            session,
            languages=request.languages,
            since=as_of - NEAREST_WINDOW,
            until=as_of,
            profile=profile,
            limit=NEAREST_LIMIT,
        )
    if reader.signals.followed_stories and request.view != "top":
        rows += await repo.story_candidates(
            session,
            languages=request.languages,
            since=as_of - NEAREST_WINDOW,
            until=as_of,
            story_ids=set(reader.signals.followed_stories),
            profile=profile,
        )

    unique: dict[int, repo.CandidateRow] = {}
    for row in rows:
        if row.article_id not in unique and row.article_id not in reader.excluded:
            unique[row.article_id] = row
    ordered = sorted(unique.values(), key=lambda r: (r.published_at, r.article_id), reverse=True)
    topics = await ranking_repo.topic_ids_by_article(session, [r.article_id for r in ordered])
    return [
        Candidate(
            article_id=row.article_id,
            source_id=row.source_id,
            story_cluster_id=row.story_cluster_id,
            language=row.language,
            published_at=row.published_at,
            trust=row.trust,
            sources=row.sources,
            languages=row.languages,
            topic_ids=frozenset(topics.get(row.article_id, ())),
            similarity=row.similarity,
        )
        for row in ordered
    ]


def _with_popularity(signals: Signals, counts: dict[int, tuple[int, int]]) -> Signals:
    """Recent click-through per article, against a 5% base rate: opens per
    time seen, not raw opens - a card everyone is shown first is not popular
    for being opened by some of them."""
    popularity = {
        article_id: scoring.lift(opened, seen, BASE_CTR, strength=CTR_PRIOR_STRENGTH)
        for article_id, (seen, opened) in counts.items()
    }
    return Signals(
        languages=signals.languages,
        topic_lift=signals.topic_lift,
        source_lift=signals.source_lift,
        followed_topics=signals.followed_topics,
        followed_sources=signals.followed_sources,
        followed_stories=signals.followed_stories,
        fatigue=signals.fatigue,
        seen=signals.seen,
        popularity=popularity,
    )


def _explorable(
    pooled: list[Candidate], signals: Signals, weights: scoring.Weights, as_of: datetime
) -> npt.NDArray[np.bool_]:
    """Stories an exploration slot may show: among the pool's most important
    by the non-personal score, none of whose topics the reader already reads
    or follows."""
    base = [scoring.base_score(c, weights, now=as_of) for c in pooled]
    important = set(sorted(range(len(pooled)), key=lambda i: (-base[i], i))[:EXPLORE_POOL])
    return np.array(
        [
            index in important
            and not (c.topic_ids & signals.followed_topics)
            and all(signals.topic_lift.get(t, 0.0) <= 0.0 for t in c.topic_ids)
            for index, c in enumerate(pooled)
        ],
        dtype=bool,
    )


def _reason(
    candidate: Candidate,
    placement: scoring.Placement,
    signals: Signals,
    clicks: dict[int, int],
) -> RankReason | None:
    """The one term that moved this card, in a fixed order of how specific it
    is to the reader. Only terms the scorer actually applied."""
    if placement.exploration:
        return RankReason(kind="exploration")
    if candidate.story_cluster_id is not None and (
        candidate.story_cluster_id in signals.followed_stories
    ):
        return RankReason(kind="followed_story")
    followed = sorted(candidate.topic_ids & signals.followed_topics)
    if followed:
        return RankReason(kind="followed_topic", topic_id=followed[0])
    if candidate.source_id in signals.followed_sources:
        return RankReason(kind="followed_source")
    if candidate.similarity is not None and candidate.similarity >= SIMILAR_REASON_MIN:
        return RankReason(kind="similar")
    if clicks.get(candidate.article_id, 0) >= TRENDING_MIN_CLICKS:
        return RankReason(kind="trending")
    return None


def surface_for(view: View) -> str:
    """The impression surface each view logs under."""
    return {"for_you": "feed", "top": "top", "topic": "topic"}[view]
