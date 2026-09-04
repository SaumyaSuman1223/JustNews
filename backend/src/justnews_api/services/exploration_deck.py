"""The Stage 7 exploration deck: stratified by IPTC top-level topic,
popularity-weighted within each topic, positions randomised, capped so no
topic dominates.

Reuses services.ranking's per-item scoring math (recency, source trust,
language match) inside each topic's stratum, the same way services.explore
reuses it with personalisation zeroed out - but where explore and the
heuristic ranker each produce *one* globally-ranked/diversified list, this
produces N independent per-topic pools and interleaves them, because "one
topic never crowds the rest out" is a property MMR (services.ranking.diversify)
does not guarantee: MMR trades relevance against redundancy across one global
pool, it has no notion of a topic quota. Hence a new composition function
here rather than a new call to diversify.

Followed-topic affinity and the seen-article penalty are deliberately zeroed
per stratum, same reasoning as explore.py: the point of the deck is finding
out what a reader likes, so boosting already-followed topics or suppressing
already-seen articles would bias the exact signal it exists to collect.
Popularity, source trust and language match survive, because "popular
within a topic, in the reader's language, from a trustworthy source" is what
makes a stratum's sample worth looking at rather than noise.

Sampling is a simple stratified, popularity-weighted draw - not Thompson
sampling over the 17 topic arms, which the roadmap's original design calls
for. The deck itself is what generates the first-ever exploration data in
this product; there is nothing to bandit over on day one. Thompson sampling
vs. an epsilon-greedy comparison is real future work once that data exists.

The handoff this module does NOT attempt: the roadmap's original design has
engaged articles feed a FINDING user tower, producing a vector assigned to
the nearest trained group centroid. No such model or centroid exists yet -
Stage 6 has not started. What this module does instead is log every deck
impression and interaction through the same append-only Impression/
InteractionEvent tables everything else uses, at a real (non-1.0) propensity,
under ranking_policy=DECK_POLICY - so Stage 6, once it exists, can replay
this exact history rather than needing new instrumentation retrofitted onto
readers who already did the deck.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import content as content_repo
from justnews_api.repositories import follows as follows_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import ranking as ranking_repo
from justnews_api.repositories import saves as saves_repo
from justnews_api.repositories import topics as topics_repo
from justnews_api.repositories.interactions import ImpressionToLog
from justnews_api.services import ranking
from justnews_api.services.content import parse_languages
from justnews_core.errors import ValidationError

DECK_POLICY = "exploration_deck_v1"
DECK_SURFACE = "onboarding"

DECK_SIZE = 20
PER_TOPIC_CAP = 3  # "capped so no topic dominates" - a hard ceiling per topic
CANDIDATE_POOL_PER_TOPIC = 30

# A reader needs at least this many distinct-article strong-signal
# interactions (click, save, share - never not_interested) with one topic
# during the deck before it counts as a real follow. See
# record_deck_engagement: one click is weak evidence (could be idle
# curiosity, could just be where the weighted draw happened to place an
# unpopular article) - this is a plain small-integer heuristic, matching how
# recent_click_counts and friends already favour simple arithmetic over
# anything statistical, consistent with there being no real usage data yet
# to tune a fancier threshold against.
DECK_FOLLOW_THRESHOLD = 2


@dataclass(frozen=True, slots=True)
class DeckCard:
    article: content_repo.ArticleRow
    topic_id: str
    impression_id: int | None


def _allocate_slots(n_topics: int, deck_size: int, per_topic_cap: int) -> list[int]:
    """A plain ceiling-division allocator: every topic gets ``deck_size //
    n_topics`` slots, and the remainder is spread one-each over the first
    topics, each capped. With 17 topics and a 20-card deck this gives 3
    topics 2 slots and 14 topics 1 - no topic exceeds the cap, and nothing
    fancier is warranted at this scale."""
    if n_topics == 0:
        return []
    base = min(deck_size // n_topics, per_topic_cap)
    remainder = deck_size - base * n_topics
    slots = [base] * n_topics
    for i in range(min(remainder, n_topics)):
        if slots[i] < per_topic_cap:
            slots[i] += 1
    return slots


def _weighted_sample(
    scored: list[ranking.ScoredCandidate], *, k: int, rng: random.Random
) -> list[tuple[ranking.ScoredCandidate, float]]:
    """Sequential weighted sampling without replacement. Each drawn item's
    logged propensity is its real conditional selection probability at the
    moment it was drawn (weight over the remaining pool's total weight) -
    honest for exactly the sequential mechanism actually used, which is what
    "the probability the policy had of showing that item" (CLAUDE.md) means
    for a policy that draws this way. A non-positive score (can happen: an
    unfamiliar source at trust floor times a stale article) falls back to a
    uniform draw over what's left rather than dividing by zero.
    """
    pool = list(scored)
    chosen: list[tuple[ranking.ScoredCandidate, float]] = []
    for _ in range(min(k, len(pool))):
        weights = [max(c.score, 0.0) for c in pool]
        total = sum(weights)
        if total <= 0:
            index = rng.randrange(len(pool))
            probability = 1.0 / len(pool)
        else:
            index = rng.choices(range(len(pool)), weights=weights, k=1)[0]
            probability = weights[index] / total
        chosen.append((pool.pop(index), probability))
    return chosen


async def sample_stratified(
    session: AsyncSession,
    *,
    requested_languages: list[str] | None,
    excluded: set[int],
    deck_size: int,
    per_topic_cap: int,
    candidate_pool_per_topic: int,
    rng: random.Random,
) -> list[tuple[content_repo.ArticleRow, str, float]]:
    """The shared stratified-sampling core - used both by the deck endpoint
    (full DECK_SIZE) and the feed-wide exploration mix (a small ``deck_size``
    for the trailing slots), so both draw from one implementation."""
    topics = await topics_repo.list_top_level_topics(session)
    if not topics:
        return []

    now = datetime.now(UTC)
    per_topic_target = _allocate_slots(len(topics), deck_size, per_topic_cap)

    picked: list[tuple[content_repo.ArticleRow, str, float]] = []
    already_picked_ids: set[int] = set()
    for topic, slots in zip(topics, per_topic_target, strict=True):
        if slots == 0:
            continue
        candidates = await content_repo.list_articles(
            session,
            languages=requested_languages,
            limit=candidate_pool_per_topic,
            before_published_at=None,
            before_id=None,
            exclude_article_ids=excluded | already_picked_ids,
            topic_id=topic.id,
        )
        if not candidates:
            continue
        candidate_ids = [row.id for row in candidates]
        click_counts = await ranking_repo.recent_click_counts(
            session, candidate_ids, since=now - ranking.POPULARITY_WINDOW
        )
        scored = ranking.score_candidates(
            candidates,
            topic_ids_by_article={row.id: [topic.id] for row in candidates},
            click_counts=click_counts,
            followed_topic_ids=set(),  # no affinity boost - see module docstring
            seen_article_ids=set(),  # no seen-penalty - see module docstring
            preferred_languages=requested_languages or [],
            now=now,
        )
        for candidate, probability in _weighted_sample(scored, k=slots, rng=rng):
            picked.append((candidate.article, topic.id, probability))
            already_picked_ids.add(candidate.article.id)

    rng.shuffle(picked)  # positions randomised across topics, not just within one
    return picked


async def get_exploration_deck(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_id: str,
    locale: str,
    languages: str | None,
    log_impressions: bool = True,
    rng: random.Random | None = None,
) -> list[DeckCard]:
    rng = rng or random.Random()
    requested_languages = parse_languages(languages)
    excluded = await interactions_repo.excluded_article_ids(session, user_id)

    picked = await sample_stratified(
        session,
        requested_languages=requested_languages,
        excluded=excluded,
        deck_size=DECK_SIZE,
        per_topic_cap=PER_TOPIC_CAP,
        candidate_pool_per_topic=CANDIDATE_POOL_PER_TOPIC,
        rng=rng,
    )
    if not picked:
        return []

    if not log_impressions:
        return [DeckCard(article=a, topic_id=t, impression_id=None) for a, t, _p in picked]

    impression_ids = await interactions_repo.log_impressions(
        session,
        user_id=user_id,
        session_id=session_id,
        surface=DECK_SURFACE,
        locale=locale,
        ranking_policy=DECK_POLICY,
        items=[
            ImpressionToLog(article_id=article.id, position=position, propensity=probability)
            for position, (article, _topic_id, probability) in enumerate(picked)
        ],
    )
    return [
        DeckCard(article=article, topic_id=topic_id, impression_id=impression_id)
        for (article, topic_id, _probability), impression_id in zip(
            picked, impression_ids, strict=True
        )
    ]


async def record_deck_engagement(session: AsyncSession, *, user_id: UUID, topic_id: str) -> None:
    """Called after a strong-signal deck interaction (click, save, share) is
    already recorded. If the reader has now crossed DECK_FOLLOW_THRESHOLD
    distinct articles engaged with in this topic, creates a UserFollow row.

    This bridges an otherwise-real gap: Stage 5's FOLLOWED_TOPIC_BOOST is the
    only topic-affinity signal the live ranker reads, and it reads
    UserFollow exclusively. Without this bridge, a reader who does the deck
    instead of the old checkbox picker would get strictly worse
    personalisation than the flow it replaces, for as long as Stage 6
    doesn't exist to read the richer signal directly. Revisit and remove
    once it does.

    Two sources, unioned by article id rather than summed, so an article
    that was both clicked and saved only counts once: click/share live in
    InteractionEvent, save is a separate declarative UserSave row (see
    repositories.saves's own docstring - "not an event log").

    This function only ever runs as a side effect of report_click/
    report_share (services.interactions) - deliberately not of save_article
    (services.saves), whose contract stays surface-agnostic on purpose. A
    reader whose only topic engagement is saving, with no click or share on
    that topic ever recorded, will not trigger this check. In practice a
    save follows a click-through already logged as its own signal, so this
    is a known, accepted v1 gap rather than a design flaw worth threading a
    `surface`/`topic_id` param through the declarative save path for.

    `create_follow` is idempotent (ON CONFLICT DO NOTHING on the
    user/topic unique constraint), so crossing the threshold more than once
    is a safe no-op.
    """
    if not topic_id.strip():
        raise ValidationError("topic_id is required.")
    clicked_or_shared = await interactions_repo.distinct_article_ids_with_event(
        session,
        user_id=user_id,
        surface=DECK_SURFACE,
        topic_id=topic_id,
        event_types=("click", "share"),
    )
    saved = await saves_repo.saved_article_ids_in_topic(session, user_id, topic_id)
    if len(clicked_or_shared | saved) >= DECK_FOLLOW_THRESHOLD:
        await follows_repo.create_follow(session, user_id, topic_id)
