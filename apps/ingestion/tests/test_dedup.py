"""The three deduplication layers, against a real database.

These are the tests that matter most in Stage 1. Getting dedup wrong is
visible on the front page in both directions: too loose and unrelated stories
merge, too tight and the same wire story appears eight times.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.embedding import HashingEmbedder, embed_article_text
from justnews_core.models import Article, StoryCluster
from justnews_core.settings import Settings
from justnews_core.text import canonicalise_url, simhash64
from justnews_ingestion import dedup

SETTINGS = Settings()
EMBEDDER = HashingEmbedder()


def _candidate(title: str, url: str, snippet: str | None = None) -> dict[str, object]:
    return {
        "url_canonical": canonicalise_url(url),
        "simhash": simhash64(title),
        "embedding": embed_article_text(EMBEDDER, title, snippet),
        "published_at": datetime.now(UTC),
    }


class TestLayerOneCanonicalUrl:
    async def test_an_unseen_url_is_new(self, session: AsyncSession) -> None:
        await make_source(session)
        verdict = await dedup.classify_candidate(
            session, settings=SETTINGS, **_candidate("Fresh story", "https://a.com/1")
        )
        assert verdict.kind == "new"
        assert verdict.should_store

    async def test_the_same_url_is_a_duplicate(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Seen", url="https://a.com/story")
        await session.flush()

        verdict = await dedup.classify_candidate(
            session, settings=SETTINGS, **_candidate("Seen", "https://a.com/story")
        )
        assert verdict.kind == "duplicate"
        assert not verdict.should_store
        assert verdict.reason == "canonical_url"

    async def test_tracking_parameters_do_not_create_a_second_copy(
        self, session: AsyncSession
    ) -> None:
        # The single most common source of duplicates in a real feed.
        source = await make_source(session)
        await make_article(session, source, title="Seen", url="https://a.com/story")
        await session.flush()

        verdict = await dedup.classify_candidate(
            session,
            settings=SETTINGS,
            **_candidate("Seen", "https://www.a.com/story/?utm_source=twitter"),
        )
        assert verdict.kind == "duplicate"


class TestLayerTwoSimhash:
    async def test_verbatim_syndication_joins_the_original(self, session: AsyncSession) -> None:
        title = "Central bank holds interest rates steady for a third meeting"
        source_a = await make_source(session, slug="wire")
        await make_article(session, source_a, title=title, url="https://wire.com/x")
        await session.flush()

        verdict = await dedup.classify_candidate(
            session, settings=SETTINGS, **_candidate(title + ".", "https://other.com/y")
        )
        assert verdict.kind == "cluster_member"
        assert verdict.reason is not None
        assert verdict.reason.startswith("simhash_distance_")


class TestLayerThreeEmbedding:
    async def test_a_close_rewrite_clusters_by_embedding(self, session: AsyncSession) -> None:
        source = await make_source(session, slug="first")
        original = "Volcano erupts near Grindavik forcing evacuations in Iceland"
        await make_article(session, source, title=original, url="https://first.com/a")
        await session.flush()

        rewrite = "Volcano erupts near Grindavik forcing evacuation in Iceland"
        verdict = await dedup.classify_candidate(
            session, settings=SETTINGS, **_candidate(rewrite, "https://second.com/b")
        )
        assert verdict.kind == "cluster_member"

    async def test_unrelated_stories_stay_separate(self, session: AsyncSession) -> None:
        # The failure that matters most: merging two genuinely different
        # stories is far worse than showing one twice.
        source = await make_source(session)
        await make_article(
            session,
            source,
            title="Volcano erupts near Grindavik in Iceland",
            url="https://a.com/volcano",
        )
        await session.flush()

        verdict = await dedup.classify_candidate(
            session,
            settings=SETTINGS,
            **_candidate("Barcelona sign teenage striker from Ajax", "https://b.com/football"),
        )
        assert verdict.kind == "new"

    async def test_the_time_window_stops_anniversary_merges(self, session: AsyncSession) -> None:
        # Without the window an anniversary piece merges with the original
        # event a year earlier.
        title = "Volcano erupts near Grindavik forcing evacuations in Iceland"
        source = await make_source(session)
        await make_article(
            session,
            source,
            title=title,
            url="https://a.com/old",
            published_at=datetime.now(UTC) - timedelta(days=365),
        )
        await session.flush()

        candidate = _candidate(title, "https://b.com/new")
        verdict = await dedup.classify_candidate(session, settings=SETTINGS, **candidate)
        assert verdict.kind == "new"
        assert verdict.reason == "no_candidates"


class TestClustering:
    async def test_a_cluster_is_created_when_the_second_article_arrives(
        self, session: AsyncSession
    ) -> None:
        # One article is not a story yet; creating a cluster per article would
        # make the table useless.
        title = "Central bank holds interest rates steady for a third meeting"
        source_a = await make_source(session, slug="wire")
        first = await make_article(session, source_a, title=title, url="https://wire.com/x")
        await session.flush()
        assert first.story_cluster_id is None

        # Mirror the pipeline's order: classify the candidate first, then
        # store it, then attach. Classifying after the insert would find the
        # article matching itself.
        verdict = await dedup.classify_candidate(
            session, settings=SETTINGS, **_candidate(title + ".", "https://other.com/y")
        )
        assert verdict.kind == "cluster_member"

        source_b = await make_source(session, slug="other", name="Other")
        second = await make_article(session, source_b, title=title + ".", url="https://other.com/y")
        cluster = await dedup.attach_to_cluster(session, article=second, verdict=verdict)

        assert cluster is not None
        assert cluster.article_count == 2
        assert cluster.source_count == 2
        # Both test sources default to the same country - source_count is 2,
        # but that says nothing about country_count, which is a genuinely
        # different question (two publishers can share a country).
        assert cluster.country_count == 1
        await session.refresh(first)
        assert first.story_cluster_id == cluster.id

    async def test_counts_are_recomputed_not_incremented(self, session: AsyncSession) -> None:
        # Incremented counters drift the first time a write is retried.
        from justnews_core.models import StoryCluster

        source = await make_source(session)
        cluster = StoryCluster(
            title="A story",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            article_count=99,
            source_count=99,
            language_count=99,
            country_count=99,
        )
        session.add(cluster)
        await session.flush()

        for index, language in enumerate(("en", "es", "en")):
            article = await make_article(
                session, source, title=f"Coverage {index}", language=language
            )
            article.story_cluster_id = cluster.id
        await session.flush()

        await dedup.refresh_cluster_counts(session, cluster)
        assert cluster.article_count == 3
        assert cluster.language_count == 2  # en, es
        assert cluster.source_count == 1
        assert cluster.country_count == 1

    async def test_country_count_reflects_distinct_publisher_countries(
        self, session: AsyncSession
    ) -> None:
        from justnews_core.models import StoryCluster

        uk_source = await make_source(session, slug="uk-wire", country="GB")
        us_source = await make_source(session, slug="us-wire", country="US")
        # A source with no recorded country - it must not count as a third,
        # "unknown" country; it should simply not add to the count.
        unknown_source = await make_source(session, slug="no-country", country=None)

        cluster = StoryCluster(
            title="A story with three publishers",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        session.add(cluster)
        await session.flush()

        for source in (uk_source, us_source, unknown_source):
            article = await make_article(session, source, title=f"From {source.slug}")
            article.story_cluster_id = cluster.id
        await session.flush()

        await dedup.refresh_cluster_counts(session, cluster)
        assert cluster.article_count == 3
        assert cluster.source_count == 3
        assert cluster.country_count == 2


class TestRepairClusterCounts:
    """`repair-cluster-counts`, added alongside the `country_count` column
    for the clusters that predate it and sit at its default of 0."""

    async def test_dry_run_reports_but_writes_nothing(self, session: AsyncSession) -> None:
        from justnews_core.models import StoryCluster

        uk = await make_source(session, slug="uk-wire", country="GB")
        us = await make_source(session, slug="us-wire", country="US")
        cluster = StoryCluster(
            title="A story",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            # Wrong on purpose - as if this cluster predates country_count.
            country_count=0,
        )
        session.add(cluster)
        await session.flush()
        for source in (uk, us):
            article = await make_article(session, source, title=f"From {source.slug}")
            article.story_cluster_id = cluster.id
        await session.commit()

        result = await dedup.repair_cluster_counts(session, dry_run=True)
        assert result["examined"] == 1
        assert result["corrected"] == 1
        assert result["dry_run"] is True

        await session.refresh(cluster)
        assert cluster.country_count == 0, "a dry run must not write, even via a dirty ORM object"

    async def test_real_run_writes_and_a_second_run_reports_zero(
        self, session: AsyncSession
    ) -> None:
        from justnews_core.models import StoryCluster

        uk = await make_source(session, slug="uk-wire-2", country="GB")
        us = await make_source(session, slug="us-wire-2", country="US")
        cluster = StoryCluster(
            title="A story",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            country_count=0,
        )
        session.add(cluster)
        await session.flush()
        for source in (uk, us):
            article = await make_article(session, source, title=f"From {source.slug}")
            article.story_cluster_id = cluster.id
        await session.commit()

        first = await dedup.repair_cluster_counts(session, dry_run=False)
        assert first["corrected"] == 1
        await session.commit()

        await session.refresh(cluster)
        assert cluster.country_count == 2

        second = await dedup.repair_cluster_counts(session, dry_run=False)
        assert second == {"examined": 1, "corrected": 0, "dry_run": False}

    async def test_examines_every_cluster_across_more_than_one_batch(
        self, session: AsyncSession, monkeypatch
    ) -> None:
        from justnews_core.models import StoryCluster

        monkeypatch.setattr(dedup, "_REPAIR_BATCH_SIZE", 2)

        source = await make_source(session, country="GB")
        clusters = []
        for i in range(5):
            cluster = StoryCluster(
                title=f"Story {i}",
                first_seen_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
                country_count=0,
            )
            session.add(cluster)
            await session.flush()
            article = await make_article(session, source, title=f"Coverage {i}")
            article.story_cluster_id = cluster.id
            clusters.append(cluster)
        await session.commit()

        result = await dedup.repair_cluster_counts(session, dry_run=False)
        assert result["examined"] == 5
        assert result["corrected"] == 5
        for cluster in clusters:
            await session.refresh(cluster)
            assert cluster.country_count == 1


class TestNoBodyTextIsEverStored:
    def test_the_article_model_has_no_body_column(self) -> None:
        # A copyright constraint expressed as a test: we store metadata only.
        columns = set(Article.__table__.columns.keys())
        assert columns & {"body", "content", "full_text", "text", "html"} == set()


class TestUrlScreen:
    async def test_returns_only_urls_already_held(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Known", url="https://a.com/known")
        await session.flush()

        known = await dedup.filter_known_urls(
            session, ["https://a.com/known", "https://a.com/unseen"]
        )
        assert known == {"https://a.com/known"}

    async def test_empty_input_does_not_query(self, session: AsyncSession) -> None:
        assert await dedup.filter_known_urls(session, []) == set()


class TestRecentIndex:
    async def test_loads_only_the_window(self, session: AsyncSession) -> None:
        from datetime import timedelta

        source = await make_source(session)
        await make_article(session, source, title="Inside the window", minutes_ago=10)
        await make_article(
            session,
            source,
            title="Long before",
            published_at=datetime.now(UTC) - timedelta(days=30),
        )
        await session.flush()

        index = await dedup.RecentIndex.load(session, since=datetime.now(UTC) - timedelta(hours=72))
        assert len(index) == 1

    async def test_holds_scalars_not_articles(self, session: AsyncSession) -> None:
        # The point of this class: the window costs kilobytes, not megabytes of
        # vectors. Loading full rows per candidate is what made a pass overrun.
        source = await make_source(session)
        await make_article(session, source, title="Something recent")
        await session.flush()

        index = await dedup.RecentIndex.load(session, since=datetime.now(UTC) - timedelta(hours=72))
        assert all(len(row) == 4 for row in index.rows)

    async def test_articles_added_during_a_run_are_matched(self, session: AsyncSession) -> None:
        # Two entries about the same event arriving in one pass must still
        # collapse, even though the second was never in the loaded window.
        index = dedup.RecentIndex()
        now = datetime.now(UTC)
        title = "Central bank holds interest rates steady for a third meeting"
        index.add(article_id=42, simhash=simhash64(title), cluster_id=None, published_at=now)

        match = index.nearest(
            simhash64(title + "."), max_distance=3, around=now, window=timedelta(hours=72)
        )
        assert match is not None
        assert match[0] == 42

    async def test_unrelated_titles_do_not_match(self) -> None:
        index = dedup.RecentIndex()
        now = datetime.now(UTC)
        index.add(
            article_id=1,
            simhash=simhash64("Volcano erupts in Iceland"),
            cluster_id=None,
            published_at=now,
        )
        assert (
            index.nearest(
                simhash64("Barcelona sign a teenage striker"),
                3,
                around=now,
                window=timedelta(hours=72),
            )
            is None
        )

    async def test_identical_titles_weeks_apart_do_not_match(self) -> None:
        # A radio programme publishes every episode under the series name
        # ("Tech Life"). The window has to hold between the two articles, not
        # just between an article and the run clock, or three weeks of
        # unrelated episodes collapse into one "story".
        index = dedup.RecentIndex()
        now = datetime.now(UTC)
        index.add(article_id=7, simhash=simhash64("Tech Life"), cluster_id=None, published_at=now)
        assert (
            index.nearest(
                simhash64("Tech Life"),
                3,
                around=now - timedelta(days=21),
                window=timedelta(hours=72),
            )
            is None
        )


class TestEmbeddingLayerUsesTheIndex:
    async def test_nearest_by_embedding_returns_a_similarity(self, session: AsyncSession) -> None:
        from datetime import timedelta

        source = await make_source(session)
        title = "Volcano erupts near Grindavik forcing evacuations in Iceland"
        await make_article(session, source, title=title, url="https://a.com/v")
        await session.flush()

        nearest = await dedup._nearest_by_embedding(
            session,
            embedding=embed_article_text(EMBEDDER, title, None),
            since=datetime.now(UTC) - timedelta(hours=72),
            until=datetime.now(UTC) + timedelta(hours=72),
        )
        assert nearest is not None
        article, similarity = nearest
        assert article.title == title
        # Same text against itself: pgvector's cosine distance must invert to
        # a similarity near 1, not near 0. Getting this backwards would merge
        # every unrelated pair in the corpus.
        assert similarity > 0.99


class TestRepairProgrammeEpisodes:
    MARKERS = ("/sounds/", "/audio/")

    async def _cluster(self, session: AsyncSession, *articles: Article) -> StoryCluster:
        cluster = StoryCluster(
            title=articles[0].title,
            first_seen_at=articles[0].published_at,
            last_seen_at=articles[-1].published_at,
            article_count=len(articles),
            source_count=1,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()
        for article in articles:
            article.story_cluster_id = cluster.id
        await session.flush()
        return cluster

    async def test_hides_episodes_and_dissolves_their_story(self, session: AsyncSession) -> None:
        source = await make_source(session)
        episodes = [
            await make_article(
                session, source, title="Tech Life", url=f"https://bbc.co.uk/sounds/play/w{i}"
            )
            for i in range(3)
        ]
        cluster = await self._cluster(session, *episodes)
        cluster_id = cluster.id

        result = await dedup.repair_programme_episodes(session, markers=self.MARKERS)

        assert result == {"episodes_removed": 3, "clusters_dissolved": 1, "dry_run": False}
        for episode in episodes:
            assert episode.removed_at is not None
            assert episode.removed_reason == dedup.PROGRAMME_EPISODE_REMOVAL_REASON
            assert episode.story_cluster_id is None
        assert await session.get(StoryCluster, cluster_id) is None

    async def test_a_story_with_two_real_reports_survives(self, session: AsyncSession) -> None:
        source = await make_source(session)
        report_a = await make_article(session, source, title="Diets", url="https://a.com/news/1")
        report_b = await make_article(session, source, title="Diets", url="https://a.com/news/2")
        podcast = await make_article(session, source, title="Diets", url="https://a.com/audio/3")
        cluster = await self._cluster(session, report_a, report_b, podcast)

        await dedup.repair_programme_episodes(session, markers=self.MARKERS)

        assert report_a.story_cluster_id == cluster.id
        assert report_b.story_cluster_id == cluster.id
        assert cluster.article_count == 2

    async def test_dry_run_writes_nothing(self, session: AsyncSession) -> None:
        source = await make_source(session)
        episode = await make_article(
            session, source, title="Tech Now", url="https://bbc.co.uk/sounds/play/x"
        )
        report = await make_article(session, source, title="Tech Now", url="https://a.com/news/9")
        await self._cluster(session, episode, report)

        result = await dedup.repair_programme_episodes(session, markers=self.MARKERS, dry_run=True)

        assert result == {"episodes_removed": 1, "clusters_dissolved": 1, "dry_run": True}
        assert episode.removed_at is None
        assert episode.story_cluster_id is not None
