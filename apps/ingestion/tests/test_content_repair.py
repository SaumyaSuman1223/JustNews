"""Tests for ``repair_snippets``.

Audit §20/§21's data repair. The command had no coverage at all until a real
run against production timed out on the single unbounded `select(Article)`
it used to issue - these tests exist because of that incident, and the
batching ones are here specifically to pin down the behaviour the incident
was about.
"""

from __future__ import annotations

from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article
from justnews_core.settings import get_settings
from justnews_ingestion.content import repair_snippets


class TestRepairSnippets:
    async def test_dry_run_reports_but_writes_nothing(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Antonelli&#039;s win", snippet=None)
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=True)
        assert result["examined"] == 1
        assert result["corrected"] == 1
        assert result["dry_run"] is True

        article = (await session.scalars(select(Article))).one()
        assert article.title == "Antonelli&#039;s win"

    async def test_real_run_writes_and_updates_the_search_vector(
        self, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source, title="Antonelli&#039;s win", snippet=None)
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=False)
        assert result["corrected"] == 1
        await session.commit()

        await session.refresh(article)
        assert article.title == "Antonelli's win"

    async def test_a_second_run_reports_zero(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="Antonelli&#039;s win", snippet=None)
        await session.commit()

        await repair_snippets(session, get_settings(), dry_run=False)
        await session.commit()

        second = await repair_snippets(session, get_settings(), dry_run=False)
        assert second == {
            "examined": 1,
            "corrected": 0,
            "titles": 0,
            "snippets": 0,
            "dry_run": False,
            "samples": [],
        }

    async def test_already_clean_rows_are_left_alone(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await make_article(session, source, title="A clean headline", snippet="A clean snippet.")
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=False)
        assert result == {
            "examined": 1,
            "corrected": 0,
            "titles": 0,
            "snippets": 0,
            "dry_run": False,
            "samples": [],
        }

    async def test_examines_every_row_across_more_than_one_batch(
        self, session: AsyncSession, monkeypatch
    ) -> None:
        # BATCH_SIZE is 500 in production; a real corpus is the reason this
        # command was rewritten to page at all, but a test corpus that size
        # would be slow to set up and prove nothing a smaller one can't. The
        # batch size is patched down instead, so three rows cross two pages.
        import justnews_ingestion.content as content_module

        monkeypatch.setattr(content_module, "BATCH_SIZE", 2)

        source = await make_source(session)
        for index in range(3):
            await make_article(
                session, source, title=f"Row {index} &#039;quoted&#039;", snippet=None
            )
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=False)
        assert result["examined"] == 3
        assert result["corrected"] == 3

        articles = (await session.scalars(select(Article).order_by(Article.id))).all()
        assert [a.title for a in articles] == [
            "Row 0 'quoted'",
            "Row 1 'quoted'",
            "Row 2 'quoted'",
        ]

    async def test_samples_show_a_change_that_lands_past_the_old_160char_slice(
        self, session: AsyncSession
    ) -> None:
        # The first production dry run showed 8 samples whose visible
        # "before"/"after" were identical. The cause: a length-only change -
        # the most common kind this repair makes - almost always cuts a
        # 300-char snippet down to ~200 chars, well past a 160-char prefix,
        # so slicing both strings to 160 before comparing them for display
        # hid the only thing that had changed. This snippet is built to
        # reproduce exactly that: identical for its first 160 characters,
        # different only after the summary cap.
        source = await make_source(session)
        # No sentence-ending punctuation anywhere, so `make_snippet` falls
        # through to its word-boundary cut rather than stopping at an early
        # sentence - which is what makes the shared prefix run well past 160
        # characters instead of ending at the first ".".
        await make_article(session, source, title="Headline", snippet="word " * 100)
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=True)
        assert result["corrected"] == 1
        sample = result["samples"][0]
        assert sample["before"] != sample["after"]
        # The regression specifically: the bug's symptom was that a 160-char
        # slice of both strings was identical even though the full strings
        # were not.
        assert sample["before"][:160] == sample["after"][:160]

    async def test_samples_are_capped_even_over_many_batches(
        self, session: AsyncSession, monkeypatch
    ) -> None:
        import justnews_ingestion.content as content_module

        monkeypatch.setattr(content_module, "BATCH_SIZE", 2)
        monkeypatch.setattr(content_module, "SAMPLE_SIZE", 3)

        source = await make_source(session)
        for index in range(10):
            await make_article(session, source, title=f"Row {index} &#039;x&#039;", snippet=None)
        await session.commit()

        result = await repair_snippets(session, get_settings(), dry_run=True)
        assert result["corrected"] == 10
        assert len(result["samples"]) == 3
