"""Seed the taxonomy and a starting set of sources and feeds.

Idempotent: safe to run on every deploy. The feed list below is a starting
point across eight languages, not the final 250-400 of the Stage 1 target -
feeds are added and retired from the admin console in Stage 4, and a feed that
404s simply backs off and shows as unhealthy rather than breaking a run.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.language import LAUNCH_LANGUAGES
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
_EP = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/"

T_SOCIETY = "medtop:14000000"
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
        "bbc-hindi",
        "BBC News हिंदी",
        "https://www.bbc.com/hindi",
        "hi",
        "GB",
        0.9,
        (SeedFeed("https://feeds.bbci.co.uk/hindi/rss.xml", "hi"),),
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
        "france24-es",
        "France 24 Español",
        "https://www.france24.com/es",
        "es",
        "FR",
        0.8,
        (
            SeedFeed("https://www.france24.com/es/rss", "es"),
            SeedFeed("https://www.france24.com/es/economia/rss", "es", T_ECON),
            SeedFeed("https://www.france24.com/es/deportes/rss", "es", T_SPORT),
            SeedFeed("https://www.france24.com/es/cultura/rss", "es", T_ARTS),
        ),
    ),
    SeedSource(
        "elpais",
        "El País",
        "https://elpais.com",
        "es",
        "ES",
        0.85,
        (
            SeedFeed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "es"),
            SeedFeed(_EP + "economia/portada", "es", T_ECON),
            SeedFeed(_EP + "deportes/portada", "es", T_SPORT),
            SeedFeed(_EP + "tecnologia/portada", "es", T_SCI),
            SeedFeed(_EP + "ciencia/portada", "es", T_SCI),
            SeedFeed(_EP + "cultura/portada", "es", T_ARTS),
            SeedFeed(_EP + "sociedad/portada", "es", T_SOCIETY),
            SeedFeed(_EP + "internacional/portada", "es", T_POL),
        ),
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
        "ndtv-india",
        "NDTV India",
        "https://ndtv.in",
        "hi",
        "IN",
        0.8,
        (
            SeedFeed("https://feeds.feedburner.com/ndtvkhabar-latest", "hi"),
            SeedFeed("https://feeds.feedburner.com/ndtvkhabar-india", "hi"),
            SeedFeed("https://feeds.feedburner.com/ndtvkhabar-business", "hi", T_ECON),
            SeedFeed("https://feeds.feedburner.com/ndtvkhabar-cricket", "hi", T_SPORT),
            SeedFeed("https://feeds.feedburner.com/ndtvkhabar-world", "hi", T_POL),
        ),
    ),
    SeedSource(
        "amar-ujala",
        "Amar Ujala",
        "https://www.amarujala.com",
        "hi",
        "IN",
        0.75,
        (
            SeedFeed("https://www.amarujala.com/rss/india-news.xml", "hi"),
            SeedFeed("https://www.amarujala.com/rss/business.xml", "hi", T_ECON),
            SeedFeed("https://www.amarujala.com/rss/sports.xml", "hi", T_SPORT),
            SeedFeed("https://www.amarujala.com/rss/technology.xml", "hi", T_SCI),
            SeedFeed("https://www.amarujala.com/rss/entertainment.xml", "hi", T_ARTS),
            SeedFeed("https://www.amarujala.com/rss/world.xml", "hi", T_POL),
        ),
    ),
    SeedSource(
        "aaj-tak",
        "आज तक",
        "https://www.aajtak.in",
        "hi",
        "IN",
        0.75,
        (SeedFeed("https://www.aajtak.in/rssfeeds/?id=home", "hi"),),
    ),
    SeedSource(
        "abp-live",
        "ABP Live",
        "https://www.abplive.com",
        "hi",
        "IN",
        0.7,
        (
            SeedFeed("https://www.abplive.com/news/india/feed", "hi"),
            SeedFeed("https://www.abplive.com/business/feed", "hi", T_ECON),
            SeedFeed("https://www.abplive.com/sports/feed", "hi", T_SPORT),
            SeedFeed("https://www.abplive.com/technology/feed", "hi", T_SCI),
            SeedFeed("https://www.abplive.com/entertainment/feed", "hi", T_ARTS),
        ),
    ),
)

SEED_EDITIONS: tuple[tuple[str, str, str, str | None, bool], ...] = (
    ("en-US", "United States", "en", "US", True),
    ("en-GB", "United Kingdom", "en", "GB", False),
    ("en-IN", "India", "en", "IN", False),
    ("es-ES", "España", "es", "ES", False),
    ("es-MX", "México", "es", "MX", False),
    ("hi-IN", "भारत", "hi", "IN", False),
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


async def find_orphaned_feeds(session: AsyncSession) -> list[str]:
    """Active feeds in the database that this seed list no longer contains.

    Seeding is additive on purpose: from Stage 4 the admin console adds sources
    that were never in this file, and deleting anything absent from the list
    would take those with it. But a feed dropped from the list stays active and
    keeps failing forever, so it is reported rather than removed - deactivating
    it is an operator decision.

    ``justnews-ingest retire-languages`` is the narrow, deliberate version of
    that decision: it deactivates only what targets a language this product no
    longer ships, which is the one case where "absent from the seed list" is
    unambiguous rather than a judgement call.
    """
    seeded = {feed.url for source in SEED_SOURCES for feed in source.feeds}
    result = await session.execute(select(Feed.url).where(Feed.active.is_(True)))
    return sorted(url for url in result.scalars().all() if url not in seeded)


async def retire_unshipped_languages(session: AsyncSession) -> dict[str, int]:
    """Deactivate every source and feed targeting a language we no longer ship.

    Deactivated, never deleted: ``sources`` cascades to ``articles``, so
    deleting a dropped source would take its whole archive with it - including
    the impressions and interaction events that reference those articles, which
    are the training data Stage 6 depends on. Flipping ``active`` stops the
    ingestion run from fetching them while leaving all of it intact, and is
    reversible by re-adding the language.

    Narrower than "anything not in SEED_SOURCES" on purpose: that would also
    catch admin-added sources and the publishers GNews backfill discovers on
    its own, which are legitimate content in a language we do ship.
    """
    shipped = list(LAUNCH_LANGUAGES)

    feeds = await session.execute(
        update(Feed)
        .where(Feed.active.is_(True), Feed.language.not_in(shipped))
        .values(active=False)
        .returning(Feed.id)
    )
    sources = await session.execute(
        update(Source)
        .where(Source.active.is_(True), Source.language.not_in(shipped))
        .values(active=False)
        .returning(Source.id)
    )
    # Editions are deleted rather than deactivated - they have no `active`
    # column and, uniquely, nothing references them (no foreign key points at
    # `editions`), so removing one destroys nothing downstream. A source cannot
    # be treated this way, which is why the two are handled differently here.
    editions = await session.execute(
        delete(Edition).where(Edition.language.not_in(shipped)).returning(Edition.id)
    )
    result = {
        "feeds_deactivated": len(feeds.scalars().all()),
        "sources_deactivated": len(sources.scalars().all()),
        "editions_deleted": len(editions.scalars().all()),
    }
    log.info("retire_unshipped_languages", **result, shipped=shipped)
    return result


async def seed_all(session: AsyncSession) -> dict[str, int]:
    topics = await seed_topics(session)
    editions = await seed_editions(session)
    sources, feeds = await seed_sources(session)
    orphaned = await find_orphaned_feeds(session)

    result = {"topics": topics, "editions": editions, "sources": sources, "feeds": feeds}
    log.info("seed_complete", **result, orphaned_feeds=len(orphaned))
    if orphaned:
        log.warning("seed_orphaned_feeds", urls=orphaned[:10])
    return result | {"orphaned_feeds": len(orphaned)}
