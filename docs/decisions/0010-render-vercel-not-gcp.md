# 0010 — Render and Vercel instead of GCP Cloud Run

- **Date:** 2026-09-02
- **Status:** accepted — supersedes the Cloud Run portions of ADR 0003

## Context

ADR 0003 chose GCP Cloud Run for the API and ingestion, reasoned around its
specific always-free allowance (2M req/mo, 180k vCPU-s, scale-to-zero,
US-only regions). Stage 0 scaffolded that plan as Terraform
(`infra/terraform/envs/gcp`) but it was never applied: no GCP project, no
billing account, no Terraform state bucket, no Workload Identity Federation
for GitHub Actions — none of it existed. Stage 5 shipped a heuristic ranker
whose own "done when" needs real beta CTR, which needs a live site, which
this gap was blocking.

The web app was always going to Vercel — that part of ADR 0001 doesn't
change. What changes is the API's host, and, as a direct consequence, where
ingestion runs.

## Decision

**API → Render, free tier**, deployed from `render.yaml` (a Render
Blueprint). Render's git integration deploys on every push to `main` —
same effect as the Cloud Run plan's "`main` → staging deploy," with zero
custom deploy workflow, versus GCP's requirement for Terraform, a state
backend, and either a service-account key or Workload Identity Federation
just to let GitHub Actions push an image and apply infrastructure.

**Web → Vercel**, unchanged from ADR 0001, also deploying from its own git
integration.

**Ingestion → no deploy target at all.** It was already "a Cloud Run Job,
invoked by cron from GitHub Actions" — the schedule lived in
`.github/workflows/ingest.yml` regardless of where the job itself ran.
Render's free tier doesn't offer cron/background-worker services without a
paid plan, but the ingestion CLI never needed a long-lived host — it's a
bounded Python process (`ingest_run_deadline_seconds`) that only needs
`DATABASE_URL` and `GNEWS_API_KEY`. So it now runs directly on the scheduled
GitHub Actions runner via `uv run justnews-ingest run`, the same command
`make ingest` already runs locally. This removes a deploy target rather than
adding one.

**Database and auth stay Supabase**, unchanged — this was never a GCP
decision.

## Consequences

**Easy:** no cloud account to create beyond what already exists (Render,
Vercel, GitHub are all sign-in-with-GitHub), no Terraform state to manage,
no IAM to reason about. Rollback is a dashboard button on both platforms
(`docs/runbook.md`).

**Given up:** Cloud Run's documented always-free ceiling (2M req/mo, 180k
vCPU-s) is a known, generous number; Render's free-tier limits are taken on
trust from its current pricing page rather than re-derived here the way
ADR 0003 measured GCP's. Re-check them before Stage 8's launch gate, when
real traffic makes the ceiling relevant for the first time.

**A real trade-off, not measured here:** Render's free web services spin
down after 15 minutes idle and cold-start on the next request — the same
kind of latency hit Cloud Run's scale-to-zero already accepted, not
benchmarked against it. ADR 0003's mitigations apply unchanged and do the
same job: anonymous/cacheable routes render on Vercel's edge and never
reach the API, and a slow or cold API degrades to chronological ranking
rather than failing the request.

**Revisit if:** beta usage grows enough that Render's single free instance
becomes the bottleneck, or Stage 8's launch gate needs a real
staging/production split — at that point a second Render service (from the
same `render.yaml` pattern) is the addition, not a new platform.
