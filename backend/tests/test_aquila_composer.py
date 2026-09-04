"""Integration tests for the Aquila issue composer.

The composer is the only thing that decides what a reader sees in Aquila, and
it runs unattended three times a day, so the properties worth pinning are the
ones a bad run would quietly violate: no duplicate issue, no story twice in
one paper, no outlet owning a page, and no publishing at all when the corpus
cannot support a paper.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count

from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import ArticleTopic, Issue, IssuePage, IssueSlot, StoryCluster
from justnews_ingestion.aquila import (
    MAX_PER_SOURCE_PER_PAGE,
    MIN_ARTICLES_FOR_ISSUE,
    compose_issue,
    current_slot,
)

POLITICS = "medtop:11000000"


_corpus_calls = count(start=1)


async def _corpus(
    session: AsyncSession, *, count: int = 20, language: str = "en", sources: int = 4
) -> None:
    """A corpus wide enough to fill a front page, spread over several sources.

    Slugs carry a per-call prefix because `sources.slug` is unique and a test
    that builds two corpora (an English one and a Spanish one, say) would
    otherwise collide on its second call.
    """
    batch = next(_corpus_calls)
    made = [await make_source(session, slug=f"src-{batch}-{i}") for i in range(sources)]
    for i in range(count):
        await make_article(
            session,
            made[i % sources],
            title=f"Headline {i}",
            language=language,
            minutes_ago=i * 3,
        )


class TestComposeIssue:
    async def test_publishes_a_front_page(self, session: AsyncSession) -> None:
        await _corpus(session)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        assert result.issue_id is not None
        assert result.skipped_reason is None
        assert result.pages >= 1
        assert result.articles > 0

        pages = (
            await session.scalars(
                select(IssuePage)
                .where(IssuePage.issue_id == result.issue_id)
                .order_by(IssuePage.page_no)
            )
        ).all()
        assert pages[0].page_no == 1
        assert pages[0].topic_id is None, "page 1 is the front, drawn from the whole corpus"

        roles = (
            await session.scalars(select(IssueSlot.role).where(IssueSlot.page_id == pages[0].id))
        ).all()
        assert roles.count("lead") == 1, "exactly one lead on the front page"
        assert "secondary" in roles and "brief" in roles

    async def test_masthead_numbering_increments(self, session: AsyncSession) -> None:
        await _corpus(session)
        await session.commit()

        first = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()
        second = await compose_issue(session, locale="en", edition_slot="midday")
        await session.commit()

        assert first.volume == second.volume
        assert second.number == first.number + 1

    async def test_recomposing_the_same_edition_is_a_no_op(self, session: AsyncSession) -> None:
        """The workflow can be re-run, and a retry must not publish twice."""
        await _corpus(session)
        await session.commit()

        first = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()
        again = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        assert again.issue_id == first.issue_id
        assert again.skipped_reason == "already_published"
        still_there = await session.scalar(select(Issue.id).where(Issue.id == first.issue_id))
        assert still_there is not None

    async def test_thin_corpus_publishes_nothing(self, session: AsyncSession) -> None:
        """A quiet night is an ordinary Tuesday, not an error."""
        await _corpus(session, count=MIN_ARTICLES_FOR_ISSUE - 1)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        assert result.issue_id is None
        assert result.skipped_reason == "corpus_too_thin"
        assert (await session.scalars(select(Issue))).all() == []

    async def test_only_the_locale_language_is_printed(self, session: AsyncSession) -> None:
        """No query returns content in a language the reader did not ask for."""
        await _corpus(session, count=20, language="en")
        await _corpus(session, count=20, language="es", sources=2)
        await session.commit()

        result = await compose_issue(session, locale="es", edition_slot="morning")
        await session.commit()

        languages = (
            await session.scalars(
                select(IssueSlot.article_id)
                .join(IssuePage, IssuePage.id == IssueSlot.page_id)
                .where(IssuePage.issue_id == result.issue_id)
            )
        ).all()
        assert languages, "the Spanish issue should not be empty"
        from justnews_core.models import Article

        langs = (
            await session.scalars(select(Article.language).where(Article.id.in_(languages)))
        ).all()
        assert set(langs) == {"es"}

    async def test_one_article_per_story_cluster(self, session: AsyncSession) -> None:
        """A wire story reported by four outlets runs once, not four times."""
        cluster = StoryCluster(
            title="One event",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            article_count=4,
            source_count=4,
            language_count=1,
        )
        session.add(cluster)
        await session.flush()

        sources = [await make_source(session, slug=f"wire-{i}") for i in range(4)]
        for i, source in enumerate(sources):
            article = await make_article(session, source, title=f"Same story {i}", minutes_ago=i)
            article.story_cluster_id = cluster.id
        # Enough unclustered filler that the issue clears the publish floor.
        await _corpus(session, count=MIN_ARTICLES_FOR_ISSUE + 6, sources=3)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        from justnews_core.models import Article

        printed = (
            await session.scalars(
                select(Article.story_cluster_id)
                .join(IssueSlot, IssueSlot.article_id == Article.id)
                .join(IssuePage, IssuePage.id == IssueSlot.page_id)
                .where(IssuePage.issue_id == result.issue_id)
            )
        ).all()
        clustered = [c for c in printed if c == cluster.id]
        assert len(clustered) <= 1, "the same story cluster must not run twice in one issue"

    async def test_no_source_dominates_a_page(self, session: AsyncSession) -> None:
        """The per-source cap is shared across a page's roles, not per role."""
        loud = await make_source(session, slug="loud-outlet")
        for i in range(30):
            await make_article(session, loud, title=f"Loud {i}", minutes_ago=i)
        # A couple of quiet sources so the page has somewhere else to go.
        await _corpus(session, count=10, sources=3)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        from justnews_core.models import Article

        pages = (
            await session.scalars(select(IssuePage.id).where(IssuePage.issue_id == result.issue_id))
        ).all()
        for page_id in pages:
            source_ids = (
                await session.scalars(
                    select(Article.source_id)
                    .join(IssueSlot, IssueSlot.article_id == Article.id)
                    .where(IssueSlot.page_id == page_id)
                )
            ).all()
            assert source_ids.count(loud.id) <= MAX_PER_SOURCE_PER_PAGE, (
                "one outlet took more than its share of a page - the per-source "
                "budget is probably being reset between roles"
            )

    async def test_section_pages_carry_their_topic(self, session: AsyncSession) -> None:
        topic = await make_topic(session, topic_id=POLITICS, slug="politics")
        source = await make_source(session, slug="politics-source")
        for i in range(8):
            article = await make_article(session, source, title=f"Politics {i}", minutes_ago=i)
            session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await _corpus(session, count=12, sources=3)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        section = await session.scalar(
            select(IssuePage).where(
                IssuePage.issue_id == result.issue_id, IssuePage.topic_id == POLITICS
            )
        )
        assert section is not None, "a topic with plenty of coverage should get its own page"
        assert section.page_no > 1


class TestCurrentSlot:
    def test_maps_the_hour_to_the_most_recent_edition(self) -> None:
        day = datetime(2026, 9, 4, tzinfo=UTC)
        assert current_slot(day.replace(hour=7)) == "morning"
        assert current_slot(day.replace(hour=13)) == "morning"
        assert current_slot(day.replace(hour=14)) == "midday"
        assert current_slot(day.replace(hour=21)) == "midday"
        assert current_slot(day.replace(hour=22)) == "evening"

    def test_before_the_first_edition_the_paper_is_last_nights(self) -> None:
        assert current_slot(datetime(2026, 9, 4, 3, tzinfo=UTC)) == "evening"


class TestWindow:
    async def test_articles_older_than_the_window_are_not_printed(
        self, session: AsyncSession
    ) -> None:
        """Fresh news fills the paper; the widened fallback only rescues a
        genuinely quiet window, and even then stops at the fallback horizon."""
        source = await make_source(session, slug="stale")
        ancient = datetime.now(UTC) - timedelta(days=10)
        for i in range(30):
            await make_article(session, source, title=f"Old {i}", published_at=ancient)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()

        assert result.issue_id is None
        assert result.skipped_reason == "corpus_too_thin"
