"""``justnews-ingest`` - the ingestion CLI.

Every subcommand is the entry point for a scheduled GitHub Actions run - see
``.github/workflows/ingest.yml``; there is no separate deploy target
(ADR 0010). The ``run`` command is also the Supabase keep-alive: a free
project pauses after seven idle days, and the fifteen-minute cron that
fetches feeds is what stops that happening (ADR 0003).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from typing import Any

from justnews_core.db import dispose_engine, init_engine, session_scope
from justnews_core.embedding import build_embedder
from justnews_core.logging import configure_logging, get_logger
from justnews_core.settings import get_settings
from justnews_ingestion import retention
from justnews_ingestion.aquila import compose_issue, current_slot
from justnews_ingestion.classify import reclassify_untagged
from justnews_ingestion.gnews import get_quota, search
from justnews_ingestion.pipeline import run_ingestion
from justnews_ingestion.seed import retire_unshipped_languages, seed_all

log = get_logger(__name__)

FREE_TIER_BYTES = 500 * 1024 * 1024
SIZE_ALERT_FRACTION = 0.7


def _print(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, default=str) + "\n")


async def _cmd_seed(_: argparse.Namespace) -> int:
    async with session_scope() as session:
        _print(await seed_all(session))
    return 0


async def _cmd_reclassify(args: argparse.Namespace) -> int:
    async with session_scope() as session:
        _print(await reclassify_untagged(session, limit=args.limit))
    return 0


async def _cmd_retire_languages(_: argparse.Namespace) -> int:
    async with session_scope() as session:
        _print(await retire_unshipped_languages(session))
    return 0


async def _cmd_run(args: argparse.Namespace) -> int:
    settings = get_settings()
    embedder = build_embedder(settings)
    log.info("embedder_selected", name=embedder.name, dimensions=embedder.dimensions)

    stats = await run_ingestion(
        settings,
        embedder,
        feed_limit=args.feed_limit,
        enrich_articles=not args.no_enrich,
        trigger=args.trigger,
    )
    _print(asdict(stats) | {"errors": stats.errors[:10]})
    return 0


async def _cmd_prune(_: argparse.Namespace) -> int:
    settings = get_settings()
    async with session_scope() as session:
        result = await retention.prune(session, settings)
        size = await retention.database_size_bytes(session)
        articles = await retention.article_count(session)

    fraction = size / FREE_TIER_BYTES
    payload = {
        "cutoff": result.cutoff,
        "articles_deleted": result.articles_deleted,
        "clusters_deleted": result.clusters_deleted,
        "issues_deleted": result.issues_deleted,
        "articles_remaining": articles,
        "database_bytes": size,
        "free_tier_fraction": round(fraction, 3),
    }
    if fraction >= SIZE_ALERT_FRACTION:
        payload["alert"] = (
            f"Database is at {fraction:.0%} of the 500 MB free tier. "
            f"Shorten the retention window or move off the free tier."
        )
        log.warning("database_size_alert", fraction=round(fraction, 3), bytes=size)
    _print(payload)
    return 0


async def _cmd_compose_aquila(args: argparse.Namespace) -> int:
    """Publish one edition of The Aquila Tribune, per locale.

    Composes for every launch locale in one run: the three publish windows
    are shared, and a paper missing in Spanish because its own workflow run
    failed is a worse outcome than one run that reports per-locale results.
    A locale whose corpus is too thin is skipped, not failed - see
    `compose_issue`.
    """
    slot = args.slot or current_slot()
    results = []
    async with session_scope() as session:
        for locale in args.locales.split(","):
            locale = locale.strip()
            if not locale:
                continue
            results.append(asdict(await compose_issue(session, locale=locale, edition_slot=slot)))
    _print({"edition_slot": slot, "issues": results})
    return 0


async def _cmd_stats(_: argparse.Namespace) -> int:
    from justnews_api.repositories.content import corpus_stats

    settings = get_settings()
    async with session_scope() as session:
        stats = await corpus_stats(session)
        quota = await get_quota(session, settings)
        size = await retention.database_size_bytes(session)

    _print(
        stats
        | {
            "database_bytes": size,
            "free_tier_fraction": round(size / FREE_TIER_BYTES, 3),
            "gnews_calls_used_today": quota.used,
            "gnews_calls_remaining_today": quota.remaining,
        }
    )
    return 0


async def _cmd_gnews(args: argparse.Namespace) -> int:
    import httpx

    settings = get_settings()
    async with session_scope() as session, httpx.AsyncClient(timeout=15.0) as client:
        entries = await search(
            session,
            client,
            settings,
            query=args.query,
            language=args.language,
            country=args.country,
        )
    _print(
        {
            "query": args.query,
            "returned": len(entries),
            "titles": [entry.title for entry in entries],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="justnews-ingest", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="seed IPTC topics, editions, sources and feeds (idempotent)")

    run = sub.add_parser("run", help="one ingestion pass over all due feeds")
    run.add_argument("--feed-limit", type=int, default=None, help="cap feeds processed this run")
    run.add_argument("--no-enrich", action="store_true", help="skip metadata scraping")
    run.add_argument("--trigger", default="cron", choices=["cron", "manual", "backfill"])

    reclassify = sub.add_parser(
        "reclassify", help="assign topics to stored articles that have none"
    )
    reclassify.add_argument("--limit", type=int, default=2000)

    sub.add_parser(
        "retire-languages",
        help="deactivate sources and feeds for languages this product no longer ships",
    )
    aquila = sub.add_parser(
        "compose-aquila", help="publish one edition of The Aquila Tribune per locale"
    )
    aquila.add_argument(
        "--slot",
        default=None,
        choices=["morning", "midday", "evening"],
        help="which edition; defaults to whichever publish time most recently passed",
    )
    aquila.add_argument("--locales", default="en,es,hi", help="comma-separated locales to compose")

    sub.add_parser("prune", help="apply the retention window and report database size")
    sub.add_parser("stats", help="corpus size, language spread and quota usage")

    gnews = sub.add_parser("gnews", help="one GNews search (costs one call from today's budget)")
    gnews.add_argument("query")
    gnews.add_argument("--language", default="en")
    gnews.add_argument("--country", default=None)

    return parser


_COMMANDS = {
    "seed": _cmd_seed,
    "run": _cmd_run,
    "reclassify": _cmd_reclassify,
    "retire-languages": _cmd_retire_languages,
    "prune": _cmd_prune,
    "compose-aquila": _cmd_compose_aquila,
    "stats": _cmd_stats,
    "gnews": _cmd_gnews,
}


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    init_engine(settings)
    try:
        return await _COMMANDS[args.command](args)
    finally:
        await dispose_engine()


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
