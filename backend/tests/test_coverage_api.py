"""Cross-language story coverage, and the blindspot rail built on it.

This is the feature that only works because clustering here is cross-lingual:
the same event reported in three languages is one story, so "who is covering
this, and in what language" and its inverse "what is nobody covering in my
language" are both questions the corpus can actually answer.
"""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import StoryCluster


async def _cluster(session: AsyncSession, title: str, *, sources: int = 2) -> StoryCluster:
    now = datetime.now(UTC)
    cluster = StoryCluster(
        title=title,
        first_seen_at=now,
        last_seen_at=now,
        article_count=0,
        source_count=sources,
        language_count=0,
    )
    session.add(cluster)
    await session.flush()
    return cluster


async def _cover(
    session: AsyncSession, cluster: StoryCluster, *, language: str, source_slug: str, title: str
) -> None:
    source = await make_source(session, slug=source_slug, language=language)
    article = await make_article(session, source, title=title, language=language)
    article.story_cluster_id = cluster.id


class TestStoryCoverage:
    async def test_reports_the_language_split_of_a_story(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        cluster = await _cluster(session, "Germany accuses Russia over airport drones")
        await _cover(session, cluster, language="en", source_slug="bbc", title="Germany accuses")
        await _cover(session, cluster, language="es", source_slug="pais", title="Alemania acusa")
        await _cover(session, cluster, language="es", source_slug="mundo", title="Alemania culpa")
        await session.commit()

        body = (await client.get(f"/v1/stories/{cluster.id}")).json()

        split = {row["language"]: row for row in body["coverage"]}
        assert split["es"]["article_count"] == 2
        assert split["es"]["source_count"] == 2
        assert split["en"]["article_count"] == 1

    async def test_the_dominant_language_leads(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # A reader scanning the chip row should see where the weight of
        # coverage actually is, not alphabetical order.
        cluster = await _cluster(session, "Widely covered in Hindi")
        await _cover(session, cluster, language="en", source_slug="one", title="Only English")
        for index in range(3):
            await _cover(
                session, cluster, language="hi", source_slug=f"hi{index}", title=f"हिंदी {index}"
            )
        await session.commit()

        body = (await client.get(f"/v1/stories/{cluster.id}")).json()
        assert body["coverage"][0]["language"] == "hi"

    async def test_a_single_language_story_reports_just_that_language(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        cluster = await _cluster(session, "Local only")
        await _cover(session, cluster, language="en", source_slug="solo", title="Only one")
        await session.commit()

        body = (await client.get(f"/v1/stories/{cluster.id}")).json()
        assert [row["language"] for row in body["coverage"]] == ["en"]


class TestBlindspots:
    async def test_surfaces_a_story_absent_from_the_readers_languages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        cluster = await _cluster(session, "Big in Hindi, absent in English")
        await _cover(session, cluster, language="hi", source_slug="ndtv", title="एक")
        await _cover(session, cluster, language="hi", source_slug="aajtak", title="दो")
        await session.commit()

        body = (await client.get("/v1/blindspots", params={"languages": "en"})).json()

        assert [item["story"]["id"] for item in body] == [cluster.id]
        assert [row["language"] for row in body[0]["coverage"]] == ["hi"]

    async def test_excludes_a_story_the_reader_can_already_read(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        cluster = await _cluster(session, "Covered in English too")
        await _cover(session, cluster, language="hi", source_slug="ndtv", title="एक")
        await _cover(session, cluster, language="en", source_slug="bbc", title="Also in English")
        await session.commit()

        body = (await client.get("/v1/blindspots", params={"languages": "en"})).json()
        assert body == []

    async def test_ignores_a_story_carried_by_a_single_outlet(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # One outlet writing something is not "the world is covering this and
        # you cannot see it" - it is one outlet writing something.
        cluster = await _cluster(session, "One outlet only", sources=1)
        await _cover(session, cluster, language="hi", source_slug="solo", title="अकेला")
        await session.commit()

        body = (await client.get("/v1/blindspots", params={"languages": "en"})).json()
        assert body == []

    async def test_no_languages_means_no_blindspots(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # "Everything is a blindspot" would be a wrong answer, not an empty
        # one - without a reader's languages there is nothing to be blind to.
        cluster = await _cluster(session, "Something")
        await _cover(session, cluster, language="hi", source_slug="ndtv", title="एक")
        await _cover(session, cluster, language="hi", source_slug="aajtak", title="दो")
        await session.commit()

        assert (await client.get("/v1/blindspots")).json() == []
