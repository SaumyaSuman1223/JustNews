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
from justnews_core.models import Article
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


class TestNoBodyTextIsEverStored:
    def test_the_article_model_has_no_body_column(self) -> None:
        # A copyright constraint expressed as a test: we store metadata only.
        columns = set(Article.__table__.columns.keys())
        assert columns & {"body", "content", "full_text", "text", "html"} == set()
