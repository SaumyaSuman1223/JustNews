"""Seed the taxonomy and a starting set of sources and feeds.

Idempotent: safe to run on every deploy. The feed list below is a starting
point across eight languages, not the final 250-400 of the Stage 1 target -
feeds are added and retired from the admin console in Stage 4, and a feed that
404s simply backs off and shows as unhealthy rather than breaking a run.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Edition, Feed, Source, Topic, TopicLabel
from justnews_core.taxonomy import TOP_LEVEL_TOPICS

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SeedFeed:
    url: str
    language: str
    topic_hint: str | None = None


@dataclass(frozen=True, slots=True)
class SeedSource:
    slug: str
    name: str
    homepage_url: str
    language: str
    country: str | None
    trust_score: float
    feeds: tuple[SeedFeed, ...]


T_ARTS = "medtop:01000000"
T_ECON = "medtop:04000000"
T_ENV = "medtop:06000000"
T_HEALTH = "medtop:07000000"
T_LIFE = "medtop:10000000"
T_POL = "medtop:11000000"
T_SCI = "medtop:13000000"
T_SPORT = "medtop:15000000"

SEED_SOURCES: tuple[SeedSource, ...] = (
    SeedSource(
        "bbc",
        "BBC News",
        "https://www.bbc.com/news",
        "en",
        "GB",
        0.9,
        (
            SeedFeed("https://feeds.bbci.co.uk/news/rss.xml", "en"),
            SeedFeed("https://feeds.bbci.co.uk/news/world/rss.xml", "en", T_POL),
            SeedFeed("https://feeds.bbci.co.uk/news/business/rss.xml", "en", T_ECON),
            SeedFeed("https://feeds.bbci.co.uk/news/technology/rss.xml", "en", T_SCI),
            SeedFeed("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", T_ENV),
            SeedFeed("https://feeds.bbci.co.uk/news/health/rss.xml", "en", T_HEALTH),
            SeedFeed("https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "en", T_ARTS),
            SeedFeed("https://feeds.bbci.co.uk/sport/rss.xml", "en", T_SPORT),
        ),
    ),
    SeedSource(
        "bbc-mundo",
        "BBC News Mundo",
        "https://www.bbc.com/mundo",
        "es",
        "GB",
        0.9,
        (SeedFeed("https://feeds.bbci.co.uk/mundo/rss.xml", "es"),),
    ),
    SeedSource(
        "bbc-arabic",
        "BBC News عربي",
        "https://www.bbc.com/arabic",
        "ar",
        "GB",
        0.9,
        (SeedFeed("https://feeds.bbci.co.uk/arabic/rss.xml", "ar"),),
    ),
    SeedSource(
        "bbc-hindi",
        "BBC News हिंदी",
        "https://www.bbc.com/hindi",
        "hi",
        "GB",
        0.9,
        (SeedFeed("https://feeds.bbci.co.uk/hindi/rss.xml", "hi"),),
    ),
    SeedSource(
        "bbc-zhongwen",
        "BBC News 中文",
        "https://www.bbc.com/zhongwen",
        "zh",
        "GB",
        0.9,
        (SeedFeed("https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "zh"),),
    ),
    SeedSource(
        "guardian",
        "The Guardian",
        "https://www.theguardian.com",
        "en",
        "GB",
        0.85,
        (
            SeedFeed("https://www.theguardian.com/world/rss", "en", T_POL),
            SeedFeed("https://www.theguardian.com/business/rss", "en", T_ECON),
            SeedFeed("https://www.theguardian.com/technology/rss", "en", T_SCI),
            SeedFeed("https://www.theguardian.com/science/rss", "en", T_SCI),
            SeedFeed("https://www.theguardian.com/environment/rss", "en", T_ENV),
            SeedFeed("https://www.theguardian.com/sport/rss", "en", T_SPORT),
            SeedFeed("https://www.theguardian.com/culture/rss", "en", T_ARTS),
            SeedFeed("https://www.theguardian.com/lifeandstyle/rss", "en", T_LIFE),
        ),
    ),
    SeedSource(
        "aljazeera",
        "Al Jazeera English",
        "https://www.aljazeera.com",
        "en",
        "QA",
        0.8,
        (SeedFeed("https://www.aljazeera.com/xml/rss/all.xml", "en"),),
    ),
    SeedSource(
        "npr",
        "NPR",
        "https://www.npr.org",
        "en",
        "US",
        0.85,
        (
            SeedFeed("https://feeds.npr.org/1001/rss.xml", "en"),
            SeedFeed("https://feeds.npr.org/1006/rss.xml", "en", T_ECON),
            SeedFeed("https://feeds.npr.org/1007/rss.xml", "en", T_SCI),
        ),
    ),
    SeedSource(
        "cbc",
        "CBC News",
        "https://www.cbc.ca/news",
        "en",
        "CA",
        0.8,
        (
            SeedFeed("https://rss.cbc.ca/lineup/topstories.xml", "en"),
            SeedFeed("https://rss.cbc.ca/lineup/world.xml", "en", T_POL),
        ),
    ),
    SeedSource(
        "abc-au",
        "ABC News (Australia)",
        "https://www.abc.net.au/news",
        "en",
        "AU",
        0.8,
        (SeedFeed("https://www.abc.net.au/news/feed/51120/rss.xml", "en"),),
    ),
    SeedSource(
        "skynews",
        "Sky News",
        "https://news.sky.com",
        "en",
        "GB",
        0.7,
        (
            SeedFeed("https://feeds.skynews.com/feeds/rss/home.xml", "en"),
            SeedFeed("https://feeds.skynews.com/feeds/rss/world.xml", "en", T_POL),
        ),
    ),
    SeedSource(
        "france24-en",
        "France 24 English",
        "https://www.france24.com/en",
        "en",
        "FR",
        0.8,
        (SeedFeed("https://www.france24.com/en/rss", "en"),),
    ),
    SeedSource(
        "france24-fr",
        "France 24",
        "https://www.france24.com/fr",
        "fr",
        "FR",
        0.8,
        (SeedFeed("https://www.france24.com/fr/rss", "fr"),),
    ),
    SeedSource(
        "france24-es",
        "France 24 Español",
        "https://www.france24.com/es",
        "es",
        "FR",
        0.8,
        (SeedFeed("https://www.france24.com/es/rss", "es"),),
    ),
    SeedSource(
        "france24-ar",
        "France 24 عربي",
        "https://www.france24.com/ar",
        "ar",
        "FR",
        0.8,
        (SeedFeed("https://www.france24.com/ar/rss", "ar"),),
    ),
    SeedSource(
        "lemonde",
        "Le Monde",
        "https://www.lemonde.fr",
        "fr",
        "FR",
        0.85,
        (
            SeedFeed("https://www.lemonde.fr/rss/une.xml", "fr"),
            SeedFeed("https://www.lemonde.fr/economie/rss_full.xml", "fr", T_ECON),
        ),
    ),
    SeedSource(
        "elpais",
        "El País",
        "https://elpais.com",
        "es",
        "ES",
        0.85,
        (SeedFeed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "es"),),
    ),
    SeedSource(
        "tagesschau",
        "tagesschau",
        "https://www.tagesschau.de",
        "de",
        "DE",
        0.85,
        (SeedFeed("https://www.tagesschau.de/xml/rss2/", "de"),),
    ),
    SeedSource(
        "spiegel",
        "Der Spiegel",
        "https://www.spiegel.de",
        "de",
        "DE",
        0.8,
        (SeedFeed("https://www.spiegel.de/schlagzeilen/tops/index.rss", "de"),),
    ),
    SeedSource(
        "g1",
        "G1",
        "https://g1.globo.com",
        "pt",
        "BR",
        0.75,
        (SeedFeed("https://g1.globo.com/rss/g1/", "pt"),),
    ),
    SeedSource(
        "thehindu",
        "The Hindu",
        "https://www.thehindu.com",
        "en",
        "IN",
        0.8,
        (
            SeedFeed("https://www.thehindu.com/news/national/feeder/default.rss", "en"),
            SeedFeed("https://www.thehindu.com/business/feeder/default.rss", "en", T_ECON),
        ),
    ),
    SeedSource(
        "verge",
        "The Verge",
        "https://www.theverge.com",
        "en",
        "US",
        0.7,
        (SeedFeed("https://www.theverge.com/rss/index.xml", "en", T_SCI),),
    ),
    SeedSource(
        "arstechnica",
        "Ars Technica",
        "https://arstechnica.com",
        "en",
        "US",
        0.75,
        (SeedFeed("https://feeds.arstechnica.com/arstechnica/index", "en", T_SCI),),
    ),
    SeedSource(
        "nature",
        "Nature",
        "https://www.nature.com",
        "en",
        "GB",
        0.95,
        (SeedFeed("https://www.nature.com/nature.rss", "en", T_SCI),),
    ),
    SeedSource(
        "nasa",
        "NASA",
        "https://www.nasa.gov",
        "en",
        "US",
        0.9,
        (SeedFeed("https://www.nasa.gov/rss/dyn/breaking_news.rss", "en", T_SCI),),
    ),
    SeedSource(
        "svt",
        "SVT Nyheter",
        "https://www.svt.se/nyheter",
        "sv",
        "SE",
        0.85,
        (SeedFeed("https://www.svt.se/nyheter/rss.xml", "sv"),),
    ),
    SeedSource(
        "nrk",
        "NRK",
        "https://www.nrk.no",
        "no",
        "NO",
        0.85,
        (SeedFeed("https://www.nrk.no/toppsaker.rss", "no"),),
    ),
    SeedSource(
        "dr",
        "DR Nyheder",
        "https://www.dr.dk/nyheder",
        "da",
        "DK",
        0.85,
        (SeedFeed("https://www.dr.dk/nyheder/service/feeds/allenyheder", "da"),),
    ),
)

SEED_EDITIONS: tuple[tuple[str, str, str, str | None, bool], ...] = (
    ("en-US", "United States", "en", "US", True),
    ("en-GB", "United Kingdom", "en", "GB", False),
    ("en-IN", "India", "en", "IN", False),
    ("es-ES", "España", "es", "ES", False),
    ("fr-FR", "France", "fr", "FR", False),
    ("de-DE", "Deutschland", "de", "DE", False),
    ("pt-BR", "Brasil", "pt", "BR", False),
    ("ar", "العالم العربي", "ar", None, False),
    ("hi-IN", "भारत", "hi", "IN", False),
    ("zh", "中文", "zh", None, False),
)


async def seed_topics(session: AsyncSession) -> int:
    """Seed the 17 IPTC top-level concepts and their labels.

    Levels 2-5 come from IPTC's published NewsCodes file via
    ``scripts/load_iptc_taxonomy.py`` - authoritative IDs are theirs, not ours.
    """
    written = 0
    for topic in TOP_LEVEL_TOPICS:
        await session.execute(
            insert(Topic)
            .values(id=topic.id, parent_id=None, level=1, path=[topic.id], slug=topic.slug)
            .on_conflict_do_update(
                index_elements=[Topic.id], set_={"slug": topic.slug, "active": True}
            )
        )
        for language, label in topic.labels.items():
            await session.execute(
                insert(TopicLabel)
                .values(topic_id=topic.id, language=language, label=label, is_official=True)
                .on_conflict_do_update(
                    index_elements=[TopicLabel.topic_id, TopicLabel.language],
                    set_={"label": label},
                )
            )
        written += 1
    return written


async def seed_editions(session: AsyncSession) -> int:
    for code, name, language, country, is_default in SEED_EDITIONS:
        await session.execute(
            insert(Edition)
            .values(
                code=code,
                name=name,
                language=language,
                country=country,
                is_default=is_default,
            )
            .on_conflict_do_update(index_elements=[Edition.code], set_={"name": name})
        )
    return len(SEED_EDITIONS)


async def seed_sources(session: AsyncSession) -> tuple[int, int]:
    sources_written = 0
    feeds_written = 0

    for seed in SEED_SOURCES:
        source_id = await session.scalar(
            insert(Source)
            .values(
                slug=seed.slug,
                name=seed.name,
                homepage_url=seed.homepage_url,
                country=seed.country,
                language=seed.language,
                trust_score=seed.trust_score,
            )
            .on_conflict_do_update(
                index_elements=[Source.slug],
                set_={"name": seed.name, "trust_score": seed.trust_score},
            )
            .returning(Source.id)
        )
        if source_id is None:
            source_id = await session.scalar(select(Source.id).where(Source.slug == seed.slug))
        sources_written += 1

        for feed in seed.feeds:
            await session.execute(
                insert(Feed)
                .values(
                    source_id=source_id,
                    url=feed.url,
                    language=feed.language,
                    topic_hint_id=feed.topic_hint,
                )
                .on_conflict_do_update(
                    index_elements=[Feed.url],
                    set_={"topic_hint_id": feed.topic_hint, "active": True},
                )
            )
            feeds_written += 1

    return sources_written, feeds_written


async def seed_all(session: AsyncSession) -> dict[str, int]:
    topics = await seed_topics(session)
    editions = await seed_editions(session)
    sources, feeds = await seed_sources(session)
    result = {"topics": topics, "editions": editions, "sources": sources, "feeds": feeds}
    log.info("seed_complete", **result)
    return result
