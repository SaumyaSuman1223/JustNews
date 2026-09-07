"""Repair stored article text.

Audit §20 and §21. Cleaning at ingestion fixes every article from now on and
nothing already in the corpus, and the corpus is what readers are looking at:
production is serving ``Antonelli&#039;s`` on Home right now, in a row written
weeks ago.

A command rather than a migration, for the same reasons as
``repair_edition_times``: it is re-runnable, it reports before it writes, and a
migration that rewrote a hundred thousand rows of text would be unreviewable in
a downgrade. Unlike the edition-times repair, this one is *lossy* - shortening
a 300-character description to a 200-character summary throws characters away -
which is why ``--dry-run`` exists and why it prints samples of what it would
change rather than only a count.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.language import tsvector_config
from justnews_core.logging import get_logger
from justnews_core.models import Article
from justnews_core.settings import Settings
from justnews_core.text import make_snippet, normalise_text

log = get_logger(__name__)

#: How many changed rows to include in the report. Enough to eyeball what the
#: rules did to real text; not so many that a repair of the whole corpus prints
#: the whole corpus.
SAMPLE_SIZE = 8

#: Rows fetched per round trip. `select(Article)` with no limit pulled every
#: row - title, snippet, embedding vector, search vector - across the pooler
#: in one shot, and against production that query timed out before returning
#: anything at all. Keyset pagination on `id` keeps each round trip small and
#: makes the command resumable in spirit: a failure partway through has
#: already committed nothing past `--dry-run`, but a future run picks up
#: where a working one left off simply by re-scanning from the start, which
#: is cheap because unchanged rows are skipped in Python, not re-written.
BATCH_SIZE = 500


def clean_article_text(
    title: str, snippet: str | None, settings: Settings
) -> tuple[str, str | None]:
    """The cleaning the ingester now applies, as a pure function.

    Shared with the pipeline through :func:`make_snippet` rather than
    reimplemented here, so a rule added to one is never missing from the other.
    """
    return (
        normalise_text(title),
        make_snippet(
            snippet,
            settings.ingest_snippet_max_chars,
            summary_max_chars=settings.ingest_summary_max_chars,
        ),
    )


async def repair_snippets(
    session: AsyncSession, settings: Settings, *, dry_run: bool = False
) -> dict[str, Any]:
    """Re-clean every stored title and snippet. Idempotent.

    Paged rather than one `select(Article)` for the whole table - see
    `BATCH_SIZE`. Ordered by `id` so a batch boundary is stable even as the
    corpus keeps ingesting underneath a long-running repair; each batch asks
    for `id > last_id`, which a concurrently inserted row (a higher id) cannot
    retroactively land inside.
    """
    examined = 0
    changed = 0
    titles_changed = 0
    snippets_changed = 0
    samples: list[dict[str, str]] = []

    last_id = 0
    while True:
        batch = (
            await session.scalars(
                select(Article).where(Article.id > last_id).order_by(Article.id).limit(BATCH_SIZE)
            )
        ).all()
        if not batch:
            break
        last_id = batch[-1].id
        examined += len(batch)

        for article in batch:
            title, snippet = clean_article_text(article.title, article.snippet, settings)
            if title == article.title and snippet == article.snippet:
                continue

            if len(samples) < SAMPLE_SIZE:
                # Full text, not a fixed-length prefix. A slice was tried
                # first and it lied: this repair's most common change is
                # trimming a 300-character snippet down to a ~200-character
                # summary, and that cut almost always lands *past* the first
                # 160 characters - a prefix of both strings is identical by
                # construction whenever that is the only thing that changed,
                # which produced samples that looked like the command had
                # done nothing on the very first production run. Both fields
                # are already bounded by the storage cap, so printing them in
                # full costs nothing and shows the actual cut.
                samples.append(
                    {
                        "id": str(article.id),
                        "before": article.snippet or article.title,
                        "after": snippet or title,
                    }
                )
            if title != article.title:
                titles_changed += 1
            if snippet != article.snippet:
                snippets_changed += 1
            changed += 1

            if not dry_run:
                article.title = title
                article.snippet = snippet
                # The search index is built from title and snippet, so leaving
                # it alone would keep the entity-laden text searchable and the
                # clean text not.
                article.search_vector = func.to_tsvector(
                    tsvector_config(article.language), f"{title} {snippet or ''}"
                )

        # Flushed per batch rather than only once at the end by the caller's
        # session_scope, so a changed row's UPDATE goes out while its batch is
        # still warm instead of all of them queuing up for one flush at the
        # close of the whole run.
        if not dry_run:
            await session.flush()

    result = {
        "examined": examined,
        "corrected": changed,
        "titles": titles_changed,
        "snippets": snippets_changed,
        "dry_run": dry_run,
        "samples": samples,
    }
    log.info("article_text_repaired", **{k: v for k, v in result.items() if k != "samples"})
    return result
