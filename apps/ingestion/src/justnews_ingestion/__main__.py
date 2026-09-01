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
from justnews_ingestion.gnews import get_quota, search
from justnews_ingestion.pipeline import run_ingestion
from justnews_ingestion.seed import seed_all

log = get_logger(__name__)

FREE_TIER_BYTES = 500 * 1024 * 1024
SIZE_ALERT_FRACTION = 0.7


def _print(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, default=str) + "\n")


async def _cmd_seed(_: argparse.Namespace) -> int:
    async with session_scope() as session:
        _print(await seed_all(session))
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
    "prune": _cmd_prune,
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
