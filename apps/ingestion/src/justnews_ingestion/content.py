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
    """Re-clean every stored title and snippet. Idempotent."""
    articles = (await session.scalars(select(Article))).all()

    changed: list[Article] = []
    samples: list[dict[str, str]] = []
    titles_changed = 0
    snippets_changed = 0

    for article in articles:
        title, snippet = clean_article_text(article.title, article.snippet, settings)
        if title == article.title and snippet == article.snippet:
            continue

        if len(samples) < SAMPLE_SIZE:
            samples.append(
                {
                    "id": str(article.id),
                    "before": (article.snippet or article.title)[:160],
                    "after": (snippet or title)[:160],
                }
            )
        if title != article.title:
            titles_changed += 1
        if snippet != article.snippet:
            snippets_changed += 1
        changed.append(article)

        if not dry_run:
            article.title = title
            article.snippet = snippet
            # The search index is built from title and snippet, so leaving it
            # alone would keep the entity-laden text searchable and the clean
            # text not.
            article.search_vector = func.to_tsvector(
                tsvector_config(article.language), f"{title} {snippet or ''}"
            )

    result = {
        "examined": len(articles),
        "corrected": len(changed),
        "titles": titles_changed,
        "snippets": snippets_changed,
        "dry_run": dry_run,
        "samples": samples,
    }
    log.info("article_text_repaired", **{k: v for k, v in result.items() if k != "samples"})
    return result
