# 0003 — Deploying on free tiers without pretending the limits do not exist

- **Date:** 2026-09-01
- **Status:** accepted — its Cloud Run specifics are superseded by
  [0010](0010-render-vercel-not-gcp.md); the free-tier reasoning for GNews,
  Supabase and retention below still holds.

## Context

The whole system must run at zero cost. Free tiers are not small paid tiers —
they fail in specific, documented ways, and a design that ignores those ways
will fall over in week three. These are the measured limits as of September 2026.

| Service | Free allowance | The failure mode it creates |
|---|---|---|
| GNews | 100 req/day, 10 articles/req, **12-hour delay**, non-commercial | The site would feel a day stale if this were the primary source |
| Supabase | 500 MB DB, 1 GB storage, 50k MAU, **pauses after 7 days idle** | Runs out of space; silently goes offline if traffic stops |
| Cloud Run | 2M req/mo, 180k vCPU-s, 360k GiB-s, **US regions only** | CPU-heavy request handling exhausts the budget; non-US latency |
| Vercel Hobby | Non-commercial, generous bandwidth | Terms violation if this is ever monetised |
| Upstash Redis | ~10k commands/day | Cannot be a general-purpose cache for every request |
| GitHub Actions | 2,000 min/mo private, unlimited public | Frequent cron on a private repo burns the budget |

## Decision

Design each limit out of the critical path rather than budgeting against it.

**GNews is demoted to a secondary source.** 150–300 RSS feeds are the primary
corpus — near-real-time, unlimited, and free. The 100 daily GNews calls are
spent on topic backfill where RSS coverage is thin, and on search. A 12-hour
delay is acceptable for backfill and unacceptable for the front page.

**Supabase's 500 MB is managed, not hoped about.** A 90-day hot retention window
with a pruning job; `halfvec` embeddings (half the bytes of `vector`);
interaction data rolled up monthly into aggregates with raw rows dropped after
180 days; a size check that alerts at 70%. Budget: ~3 KB per article including
its embedding, so ~50k live articles plus ~1M interaction rows fits with room.

**The auto-pause is defeated by the work we already do.** The ingestion cron
runs every 15 minutes and touches the database, so the project can never reach
7 idle days. An uptime check alerts if it ever does.

**Cloud Run's vCPU budget is protected by keeping the request path cheap.** No
model inference in a request (ADR 0004), aggressive `Cache-Control` +
`stale-while-revalidate` so the CDN answers most reads, and heavy work moved to
Cloud Run Jobs, which draw on the same budget but run predictably.

**The US-only region constraint is absorbed at the edge.** `api` and Supabase
sit in the same US region so DB round trips are ~1 ms. Readers elsewhere are
served mostly from Vercel's edge cache; only personalised and mutating calls
cross the ocean, and those are few per session.

**The repo stays public**, which makes Actions minutes unlimited and cron cheap.

## Consequences

- Every stage carries an operational chore: retention, pruning, quota accounting.
  These are built in Stage 4, not bolted on after something breaks.
- Migration paths are documented before they are needed: Supabase → Neon or a
  managed Postgres; Vercel Hobby → Cloudflare Pages or self-hosted Next.js on
  Cloud Run; Upstash → in-process cache. Estimated in Stage 11.
- Vercel Hobby's non-commercial terms mean monetisation requires a paid plan or
  a move. Recorded now so it is not a surprise later.
- We accept a single point of failure in Supabase. At this scale, correctly.
