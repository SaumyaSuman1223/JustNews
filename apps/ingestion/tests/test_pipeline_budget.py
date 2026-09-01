"""The run must finish before the next one starts.

Ingestion runs on a fifteen-minute GitHub Actions cron with a 12-minute
(720s) job timeout. A pass that overruns is not slow - it is killed mid-write
by whichever limit it hits first, which is how the first full run with
enrichment enabled ended. The deadline and the enrichment budget are what
make that impossible.
"""

from __future__ import annotations

import asyncio

from justnews_core.settings import Settings
from justnews_ingestion.pipeline import Deadline, RunStats


class TestDeadline:
    def test_is_not_expired_before_its_budget(self) -> None:
        assert not Deadline.after(60).expired

    def test_is_expired_once_the_budget_is_gone(self) -> None:
        assert Deadline.after(0).expired

    def test_remaining_never_goes_negative(self) -> None:
        # It is passed straight to asyncio.timeout(), which rejects negatives.
        assert Deadline.after(-5).remaining_seconds == 0.0

    async def test_remaining_is_usable_as_a_timeout(self) -> None:
        deadline = Deadline.after(0.05)
        with_timeout = asyncio.timeout(deadline.remaining_seconds)
        try:
            async with with_timeout:
                await asyncio.sleep(1)
        except TimeoutError:
            pass
        assert deadline.expired


class TestBudgets:
    def test_defaults_leave_headroom_under_the_job_timeout(self) -> None:
        # `.github/workflows/ingest.yml` caps the job at timeout-minutes: 12
        # (720s). A deadline comfortably below that guarantees the deadline
        # itself stops the run cleanly, rather than the runner killing it
        # mid-write.
        assert Settings().ingest_run_deadline_seconds < 720

    def test_deadline_fits_inside_the_cron_interval(self) -> None:
        # The cron fires every 15 minutes; overlapping runs both pass dedup on
        # the same article because neither has written what the other read.
        assert Settings().ingest_run_deadline_seconds < 15 * 60

    def test_enrichment_is_capped(self) -> None:
        settings = Settings()
        assert settings.ingest_max_enrich_per_run > 0
        assert settings.ingest_max_enrich_concurrency > 1


class TestRunStats:
    def test_records_whether_the_run_was_cut_short(self) -> None:
        # A truncated run must be visible in ingest_runs, or the corpus quietly
        # stops growing and nothing says why.
        stats = RunStats()
        assert stats.deadline_reached is False
        stats.deadline_reached = True
        assert stats.deadline_reached
