# 0001 — Initial stack

- **Date:** 2026-09-01
- **Status:** accepted — its Cloud Run choice for the API is superseded by
  [0010](0010-render-vercel-not-gcp.md); Next.js on Vercel, Supabase Postgres
  and everything else below stands.

## Context

A personalised news reader that must look and behave like a major publisher's
site, serve fast globally, and cost nothing to run. Single developer,
part-time. The ranking layer is derived from FINDING (CIKM '23), so the stack
has to accommodate PyTorch training and vector similarity search without
letting either bleed into the request path.

## Options

**1. Full JS — Next.js + tRPC + Prisma, all on Vercel.**
One language, fastest to build, best DX. But PyTorch has no place in it, the
FINDING port would need a separate Python service anyway, and Vercel's function
limits make embedding work awkward. Rejected: it wins the first month and loses
the rest.

**2. Full Python — FastAPI + Jinja/HTMX, everything on Cloud Run.**
One language, no client/server type duplication, trivially deployable. But it
gives up the edge cache, RSC streaming, and the component ecosystem that a
site of this visual ambition needs, and it makes the Expo mobile app a
from-scratch effort. Rejected: the UI bar is too high.

**3. Split — Next.js on Vercel, FastAPI on Cloud Run, Supabase Postgres.**
Two languages and a typed contract to keep in sync. Chosen.

## Decision

Option 3.

- **Next.js App Router on Vercel** for the web tier. RSC and edge caching suit a
  read-heavy site, and Vercel's free tier includes per-PR preview deploys.
- **FastAPI on Cloud Run** for the API. Python is non-negotiable given the model
  work; Cloud Run's always-free tier is the only serverless container platform
  with a genuinely permanent free allowance and scale-to-zero.
- **Supabase** for Postgres 17 + pgvector + Auth + Storage. One free project
  covers the database we wanted anyway, vector search, and an auth system we
  would otherwise spend two weeks building and owning the security of.
- **Upstash Redis** for rate limiting and hot-key caching only. Not a queue.
- **GitHub Actions cron + Cloud Run Jobs** instead of Celery — a free tier has
  no place to put an always-on worker.
- **`uv`** for Python, **`pnpm` + Turborepo** for JS, Docker Compose locally.
- **OpenAPI-generated TypeScript client** in `packages/api-client`, regenerated
  and diff-checked in CI, so the cross-language contract cannot drift silently.

## Consequences

- The API and web tiers must be independently deployable and independently
  cached. Every endpoint needs an explicit cache policy.
- Two lockfiles, two CI toolchains, two type systems. The generated client is
  the only thing preventing that from becoming a bug source.
- Cloud Run's free tier is US-region-only, so the API and database both live in
  the US. Global latency is a Vercel edge-cache problem, not an API problem.
  This is a real trade and it is revisited in Stage 11.
- Celery's absence means anything needing sub-15-minute reaction time has to be
  synchronous or use Postgres `LISTEN/NOTIFY`. Accepted; nothing in v1 needs it.
- Supabase Auth means user identity lives outside our database's foreign keys.
  We keep a `profiles` table keyed by the Supabase user ID and treat that ID as
  external.
