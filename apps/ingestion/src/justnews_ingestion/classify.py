"""Assign IPTC concepts to an article.

Order is deliberate and is the whole cost argument (ADR 0006): map the
publisher's own categories first, because that is nearly free and nearly
always right; fall back to the feed's topic hint; classify from text only for
what is left, which is a small minority.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import SourceCategoryMap
from justnews_core.taxonomy import map_category
from justnews_core.text import tokenise

# Keyword hints for the classify-from-text fallback. Deliberately small and
# conservative: a wrong topic is worse than no topic, because it teaches the
# ranker something false. Replaced by a trained classifier when the volume
# justifies one.
_KEYWORD_HINTS: dict[str, tuple[str, ...]] = {
    "medtop:15000000": ("goal", "match", "striker", "tournament", "league", "cup", "olympic"),
    "medtop:04000000": ("shares", "revenue", "inflation", "earnings", "merger", "ipo", "tariff"),
    "medtop:11000000": ("election", "parliament", "minister", "senate", "coalition", "voters"),
    "medtop:16000000": ("airstrike", "ceasefire", "troops", "offensive", "militants", "truce"),
    "medtop:13000000": ("satellite", "algorithm", "startup", "chip", "software", "spacecraft"),
    "medtop:07000000": ("outbreak", "vaccine", "hospital", "patients", "virus", "disease"),
    "medtop:17000000": ("storm", "hurricane", "typhoon", "heatwave", "rainfall", "blizzard"),
    "medtop:03000000": ("earthquake", "wildfire", "flood", "crash", "collapse", "evacuated"),
    "medtop:06000000": ("emissions", "biodiversity", "deforestation", "pollution", "wildlife"),
    "medtop:02000000": ("arrested", "convicted", "trial", "lawsuit", "prosecutors", "verdict"),
}


@dataclass(frozen=True, slots=True)
class TopicAssignment:
    topic_id: str
    confidence: float
    assigned_by: str
    is_primary: bool


async def _mapped_topics(
    session: AsyncSession, source_id: int, raw_categories: list[str]
) -> list[str]:
    """Source-specific overrides beat the built-in map."""
    if not raw_categories:
        return []
    result = await session.execute(
        select(SourceCategoryMap.raw_category, SourceCategoryMap.topic_id).where(
            SourceCategoryMap.source_id.in_([source_id, None])
        )
    )
    overrides = {raw.strip().lower(): topic for raw, topic in result.all()}

    topics: list[str] = []
    for category in raw_categories:
        topic_id = overrides.get(category.strip().lower()) or map_category(category)
        if topic_id and topic_id not in topics:
            topics.append(topic_id)
    return topics


def _keyword_topics(title: str, snippet: str | None) -> list[str]:
    tokens = set(tokenise(f"{title} {snippet or ''}"))
    scored = [
        (topic_id, sum(1 for keyword in keywords if keyword in tokens))
        for topic_id, keywords in _KEYWORD_HINTS.items()
    ]
    hits = sorted(
        ((topic_id, score) for topic_id, score in scored if score > 0),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [topic_id for topic_id, _ in hits[:2]]


async def assign_topics(
    session: AsyncSession,
    *,
    source_id: int,
    raw_categories: list[str],
    feed_topic_hint: str | None,
    title: str,
    snippet: str | None,
) -> list[TopicAssignment]:
    """Return the topics for one article, most confident first."""
    mapped = await _mapped_topics(session, source_id, raw_categories)
    if mapped:
        return [
            TopicAssignment(topic_id, 0.95 if index == 0 else 0.7, "mapping", index == 0)
            for index, topic_id in enumerate(mapped[:3])
        ]

    if feed_topic_hint:
        return [TopicAssignment(feed_topic_hint, 0.8, "feed_hint", True)]

    keyword_topics = _keyword_topics(title, snippet)
    return [
        TopicAssignment(topic_id, 0.45 if index == 0 else 0.3, "classifier", index == 0)
        for index, topic_id in enumerate(keyword_topics)
    ]
