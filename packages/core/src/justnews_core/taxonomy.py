"""IPTC Media Topics.

Topics are keyed by IPTC **concept ID**, never by label (ADR 0006). Labels are
a presentation lookup in ``topic_labels``, one row per language - which is what
lets one taxonomy serve thirteen official languages plus any we add ourselves.

The 17 top-level concepts below are seeded inline so the system works with no
network access. Levels 2-5 (1,200+ terms) are loaded from IPTC's published
NewsCodes file by ``scripts/load_iptc_taxonomy.py`` - authoritative IDs come
from IPTC, not from us.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SeedTopic:
    id: str
    slug: str
    labels: dict[str, str] = field(default_factory=dict)


# The 17 IPTC Media Topics top-level concepts.
TOP_LEVEL_TOPICS: tuple[SeedTopic, ...] = (
    SeedTopic(
        "medtop:01000000",
        "arts-culture-entertainment-media",
        {
            "en": "Arts, culture, entertainment and media",
            "es": "Arte, cultura, entretenimiento y medios",
            "fr": "Arts, culture, divertissement et médias",
            "de": "Kunst, Kultur, Unterhaltung und Medien",
            "ar": "الفنون والثقافة والترفيه والإعلام",
        },
    ),
    SeedTopic(
        "medtop:02000000",
        "crime-law-justice",
        {
            "en": "Crime, law and justice",
            "es": "Crimen, ley y justicia",
            "fr": "Criminalité, droit et justice",
            "de": "Kriminalität, Recht und Justiz",
            "ar": "الجريمة والقانون والعدالة",
        },
    ),
    SeedTopic(
        "medtop:03000000",
        "disaster-accident-emergency",
        {
            "en": "Disaster, accident and emergency incident",
            "es": "Desastre, accidente e incidente de emergencia",
            "fr": "Catastrophe, accident et situation d'urgence",
            "de": "Katastrophe, Unfall und Notfall",
            "ar": "الكوارث والحوادث والطوارئ",
        },
    ),
    SeedTopic(
        "medtop:04000000",
        "economy-business-finance",
        {
            "en": "Economy, business and finance",
            "es": "Economía, negocios y finanzas",
            "fr": "Économie, affaires et finance",
            "de": "Wirtschaft, Unternehmen und Finanzen",
            "ar": "الاقتصاد والأعمال والمال",
        },
    ),
    SeedTopic(
        "medtop:05000000",
        "education",
        {
            "en": "Education",
            "es": "Educación",
            "fr": "Éducation",
            "de": "Bildung",
            "ar": "التعليم",
        },
    ),
    SeedTopic(
        "medtop:06000000",
        "environment",
        {
            "en": "Environment",
            "es": "Medio ambiente",
            "fr": "Environnement",
            "de": "Umwelt",
            "ar": "البيئة",
        },
    ),
    SeedTopic(
        "medtop:07000000",
        "health",
        {
            "en": "Health",
            "es": "Salud",
            "fr": "Santé",
            "de": "Gesundheit",
            "ar": "الصحة",
        },
    ),
    SeedTopic(
        "medtop:08000000",
        "human-interest",
        {
            "en": "Human interest",
            "es": "Interés humano",
            "fr": "Intérêt humain",
            "de": "Vermischtes",
            "ar": "قصص إنسانية",
        },
    ),
    SeedTopic(
        "medtop:09000000",
        "labour",
        {
            "en": "Labour",
            "es": "Trabajo",
            "fr": "Travail",
            "de": "Arbeit",
            "ar": "العمل",
        },
    ),
    SeedTopic(
        "medtop:10000000",
        "lifestyle-leisure",
        {
            "en": "Lifestyle and leisure",
            "es": "Estilo de vida y ocio",
            "fr": "Style de vie et loisirs",
            "de": "Lebensstil und Freizeit",
            "ar": "أسلوب الحياة والترفيه",
        },
    ),
    SeedTopic(
        "medtop:11000000",
        "politics",
        {
            "en": "Politics",
            "es": "Política",
            "fr": "Politique",
            "de": "Politik",
            "ar": "السياسة",
        },
    ),
    SeedTopic(
        "medtop:12000000",
        "religion",
        {
            "en": "Religion",
            "es": "Religión",
            "fr": "Religion",
            "de": "Religion",
            "ar": "الدين",
        },
    ),
    SeedTopic(
        "medtop:13000000",
        "science-technology",
        {
            "en": "Science and technology",
            "es": "Ciencia y tecnología",
            "fr": "Science et technologie",
            "de": "Wissenschaft und Technik",
            "ar": "العلوم والتكنولوجيا",
        },
    ),
    SeedTopic(
        "medtop:14000000",
        "society",
        {
            "en": "Society",
            "es": "Sociedad",
            "fr": "Société",
            "de": "Gesellschaft",
            "ar": "المجتمع",
        },
    ),
    SeedTopic(
        "medtop:15000000",
        "sport",
        {
            "en": "Sport",
            "es": "Deporte",
            "fr": "Sport",
            "de": "Sport",
            "ar": "الرياضة",
        },
    ),
    SeedTopic(
        "medtop:16000000",
        "conflict-war-peace",
        {
            "en": "Conflict, war and peace",
            "es": "Conflicto, guerra y paz",
            "fr": "Conflit, guerre et paix",
            "de": "Konflikt, Krieg und Frieden",
            "ar": "النزاعات والحرب والسلام",
        },
    ),
    SeedTopic(
        "medtop:17000000",
        "weather",
        {
            "en": "Weather",
            "es": "Clima",
            "fr": "Météo",
            "de": "Wetter",
            "ar": "الطقس",
        },
    ),
)

TOP_LEVEL_IDS: frozenset[str] = frozenset(topic.id for topic in TOP_LEVEL_TOPICS)


# Common publisher category strings mapped onto top-level concepts. The
# pipeline maps first and classifies only the remainder, because mapping is
# both cheaper and more accurate than classification. Extended per source in
# ``source_category_map`` and edited from the admin console in Stage 4.
DEFAULT_CATEGORY_MAP: dict[str, str] = {
    "arts": "medtop:01000000",
    "culture": "medtop:01000000",
    "entertainment": "medtop:01000000",
    "media": "medtop:01000000",
    "film": "medtop:01000000",
    "movies": "medtop:01000000",
    "music": "medtop:01000000",
    "books": "medtop:01000000",
    "television": "medtop:01000000",
    "tv": "medtop:01000000",
    "crime": "medtop:02000000",
    "law": "medtop:02000000",
    "justice": "medtop:02000000",
    "courts": "medtop:02000000",
    "disaster": "medtop:03000000",
    "accident": "medtop:03000000",
    "emergency": "medtop:03000000",
    "business": "medtop:04000000",
    "economy": "medtop:04000000",
    "finance": "medtop:04000000",
    "markets": "medtop:04000000",
    "money": "medtop:04000000",
    "economics": "medtop:04000000",
    "education": "medtop:05000000",
    "schools": "medtop:05000000",
    "environment": "medtop:06000000",
    "climate": "medtop:06000000",
    "climate change": "medtop:06000000",
    "nature": "medtop:06000000",
    "health": "medtop:07000000",
    "medicine": "medtop:07000000",
    "wellness": "medtop:07000000",
    "coronavirus": "medtop:07000000",
    "human interest": "medtop:08000000",
    "offbeat": "medtop:08000000",
    "labour": "medtop:09000000",
    "labor": "medtop:09000000",
    "jobs": "medtop:09000000",
    "employment": "medtop:09000000",
    "lifestyle": "medtop:10000000",
    "leisure": "medtop:10000000",
    "travel": "medtop:10000000",
    "food": "medtop:10000000",
    "fashion": "medtop:10000000",
    "style": "medtop:10000000",
    "politics": "medtop:11000000",
    "government": "medtop:11000000",
    "election": "medtop:11000000",
    "elections": "medtop:11000000",
    "policy": "medtop:11000000",
    "religion": "medtop:12000000",
    "faith": "medtop:12000000",
    "science": "medtop:13000000",
    "technology": "medtop:13000000",
    "tech": "medtop:13000000",
    "space": "medtop:13000000",
    "ai": "medtop:13000000",
    "artificial intelligence": "medtop:13000000",
    "gadgets": "medtop:13000000",
    "computing": "medtop:13000000",
    "society": "medtop:14000000",
    "social": "medtop:14000000",
    "sport": "medtop:15000000",
    "sports": "medtop:15000000",
    "football": "medtop:15000000",
    "soccer": "medtop:15000000",
    "cricket": "medtop:15000000",
    "olympics": "medtop:15000000",
    "conflict": "medtop:16000000",
    "war": "medtop:16000000",
    "military": "medtop:16000000",
    "defence": "medtop:16000000",
    "defense": "medtop:16000000",
    "peace": "medtop:16000000",
    "weather": "medtop:17000000",
    "forecast": "medtop:17000000",
}


def map_category(raw_category: str) -> str | None:
    """Best-effort map of a publisher's own category string to a concept ID.

    Exact match first, then a contained-word match, so ``"World/Politics"``
    and ``"Tech News"`` both resolve. Returns None when nothing matches -
    the caller then falls back to the feed hint or the classifier.
    """
    cleaned = raw_category.strip().lower()
    if not cleaned:
        return None
    if cleaned in DEFAULT_CATEGORY_MAP:
        return DEFAULT_CATEGORY_MAP[cleaned]

    tokens = {token for token in cleaned.replace("/", " ").replace("-", " ").split() if token}
    for key, topic_id in DEFAULT_CATEGORY_MAP.items():
        if " " not in key and key in tokens:
            return topic_id
    for key, topic_id in DEFAULT_CATEGORY_MAP.items():
        if " " in key and key in cleaned:
            return topic_id
    return None
