"""Assign IPTC concepts to an article.

Order is deliberate and is the whole cost argument (ADR 0006): map the
publisher's own categories first, because that is nearly free and nearly
always right; fall back to the feed's topic hint; classify from text only for
what is left, which is a small minority.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article, ArticleTopic, Feed, SourceCategoryMap
from justnews_core.taxonomy import map_category
from justnews_core.text import tokenise

log = get_logger(__name__)

# Keyword hints for the classify-from-text fallback. Deliberately small and
# conservative: a wrong topic is worse than no topic, because it teaches the
# ranker something false. Replaced by a trained classifier when the volume
# justifies one.
#
# One tuple per language per topic. This used to be English-only, which meant
# every Spanish and Hindi article that arrived through a general feed - i.e.
# most of them - fell through all three classification paths and ended up with
# no topic at all. Terms are surface forms, not stems, because nothing here
# stems: they have to match tokens as they actually appear in a headline.
_KEYWORD_HINTS: dict[str, tuple[str, ...]] = {
    # Sport
    "medtop:15000000": (
        "goal",
        "match",
        "striker",
        "tournament",
        "league",
        "cup",
        "olympic",
        "gol",
        "partido",
        "liga",
        "torneo",
        "campeonato",
        "futbolista",
        "क्रिकेट",
        "मैच",
        "टीम",
        "खिलाड़ी",
        "टूर्नामेंट",
        "पारी",
    ),
    # Economy, business and finance
    "medtop:04000000": (
        "shares",
        "revenue",
        "inflation",
        "earnings",
        "merger",
        "ipo",
        "tariff",
        "acciones",
        "inflación",
        "ingresos",
        "bolsa",
        "aranceles",
        "beneficios",
        "शेयर",
        "बाजार",
        "अर्थव्यवस्था",
        "महंगाई",
        "निवेश",
        "कारोबार",
    ),
    # Politics
    "medtop:11000000": (
        "election",
        "parliament",
        "minister",
        "senate",
        "coalition",
        "voters",
        "elecciones",
        "parlamento",
        "ministro",
        "senado",
        "votantes",
        "diputados",
        "चुनाव",
        "संसद",
        "मंत्री",
        "सरकार",
        "विधानसभा",
        "मतदान",
    ),
    # Conflict, war and peace
    "medtop:16000000": (
        "airstrike",
        "ceasefire",
        "troops",
        "offensive",
        "militants",
        "truce",
        "bombardeo",
        "tropas",
        "ofensiva",
        "milicianos",
        "tregua",
        "युद्ध",
        "सैनिक",
        "सेना",
        "संघर्ष",
        "हवाई",
    ),
    # Science and technology
    "medtop:13000000": (
        "satellite",
        "algorithm",
        "startup",
        "chip",
        "software",
        "spacecraft",
        "satélite",
        "algoritmo",
        "científicos",
        "informática",
        "वैज्ञानिक",
        "सॉफ्टवेयर",
        "उपग्रह",
        "तकनीक",
    ),
    # Health
    "medtop:07000000": (
        "outbreak",
        "vaccine",
        "hospital",
        "patients",
        "virus",
        "disease",
        "vacuna",
        "pacientes",
        "enfermedad",
        "sanitario",
        "contagios",
        "अस्पताल",
        "वैक्सीन",
        "मरीज",
        "बीमारी",
        "इलाज",
    ),
    # Weather
    "medtop:17000000": (
        "storm",
        "hurricane",
        "typhoon",
        "heatwave",
        "rainfall",
        "blizzard",
        "tormenta",
        "huracán",
        "lluvias",
        "nevada",
        "sequía",
        "तूफान",
        "बारिश",
        "मौसम",
        "लू",
    ),
    # Disaster, accident and emergency
    "medtop:03000000": (
        "earthquake",
        "wildfire",
        "flood",
        "crash",
        "collapse",
        "evacuated",
        "terremoto",
        "incendio",
        "inundación",
        "derrumbe",
        "evacuados",
        "भूकंप",
        "बाढ़",
        "हादसा",
        "दुर्घटना",
    ),
    # Environment
    "medtop:06000000": (
        "emissions",
        "biodiversity",
        "deforestation",
        "pollution",
        "wildlife",
        "emisiones",
        "contaminación",
        "biodiversidad",
        "deforestación",
        "प्रदूषण",
        "जलवायु",
        "पर्यावरण",
    ),
    # Crime, law and justice
    "medtop:02000000": (
        "arrested",
        "convicted",
        "trial",
        "lawsuit",
        "prosecutors",
        "verdict",
        "detenido",
        "juicio",
        "fiscal",
        "condenado",
        "tribunal",
        "गिरफ्तार",
        "अदालत",
        "आरोपी",
        "मुकदमा",
    ),
    # Arts, culture, entertainment and media
    "medtop:01000000": (
        "album",
        "festival",
        "novel",
        "filmmaker",
        "soundtrack",
        "película",
        "cineasta",
        "álbum",
        "estreno",
        "फिल्म",
        "अभिनेता",
        "अभिनेत्री",
        "बॉलीवुड",
    ),
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
    hint_assigned_by: str = "feed_hint",
) -> list[TopicAssignment]:
    """Return the topics for one article, most confident first.

    ``hint_assigned_by`` labels where ``feed_topic_hint`` came from. It is a
    feed's own section by default, but GNews backfill supplies a topic from the
    category it requested, and recording that distinctly keeps the provenance
    honest - the two are equally confident but are not the same evidence.
    """
    mapped = await _mapped_topics(session, source_id, raw_categories)
    if mapped:
        return [
            TopicAssignment(topic_id, 0.95 if index == 0 else 0.7, "mapping", index == 0)
            for index, topic_id in enumerate(mapped[:3])
        ]

    if feed_topic_hint:
        return [TopicAssignment(feed_topic_hint, 0.8, hint_assigned_by, True)]

    keyword_topics = _keyword_topics(title, snippet)
    return [
        TopicAssignment(topic_id, 0.45 if index == 0 else 0.3, "classifier", index == 0)
        for index, topic_id in enumerate(keyword_topics)
    ]


async def reclassify_untagged(session: AsyncSession, *, limit: int) -> dict[str, int]:
    """Assign topics to stored articles that have none.

    Exists because classification quality is a moving target - the keyword
    hints gained Spanish and Hindi terms long after those articles were
    ingested - and an article is only classified once, at ingest. Without this,
    fixing the classifier only helps content that has not arrived yet.

    Only articles with *no* topic at all are touched. Re-running the classifier
    over already-tagged articles would let a weak keyword match (confidence
    0.45) overwrite a publisher category mapping (0.95), which is strictly
    worse information.

    ``raw_categories`` is not stored - it is transient ingest-time data - so
    this can only use the feed hint and the keyword fallback. That is precisely
    the gap it exists to close.
    """
    untagged = (
        select(Article.id, Article.source_id, Article.title, Article.snippet, Feed.topic_hint_id)
        .join(Feed, Article.feed_id == Feed.id, isouter=True)
        .outerjoin(ArticleTopic, ArticleTopic.article_id == Article.id)
        .where(ArticleTopic.article_id.is_(None))
        .limit(limit)
    )
    rows = (await session.execute(untagged)).all()

    assigned = 0
    for article_id, source_id, title, snippet, feed_hint in rows:
        topics = await assign_topics(
            session,
            source_id=source_id,
            raw_categories=[],
            feed_topic_hint=feed_hint,
            title=title,
            snippet=snippet,
        )
        if not topics:
            continue
        for topic in topics:
            await session.execute(
                insert(ArticleTopic)
                .values(
                    article_id=article_id,
                    topic_id=topic.topic_id,
                    confidence=topic.confidence,
                    is_primary=topic.is_primary,
                    assigned_by=topic.assigned_by,
                )
                .on_conflict_do_nothing(
                    index_elements=[ArticleTopic.article_id, ArticleTopic.topic_id]
                )
            )
        assigned += 1

    result = {"examined": len(rows), "assigned": assigned}
    log.info("reclassify_untagged", **result)
    return result
