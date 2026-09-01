# CLAUDE.md

How to work in this repo.

## Project

**JustNews** — a personalised, multilingual news reader with the polish of a
major publisher's site, for a global audience, ranked by a model derived from
FINDING (Yu et al., CIKM '23), running entirely on free tiers.

Read `docs/ROADMAP.md` first. It is the plan of record.

## Stack

- **web** — Next.js App Router, TypeScript, Tailwind, TanStack Query, i18n + RTL → Vercel
- **api** — FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2 async, Alembic → Cloud Run
- **ingestion** — Python, RSS + GNews + metadata scraping → Cloud Run Job, cron from GitHub Actions
- **db** — Supabase Postgres 17 + pgvector (`halfvec`)
- **auth** — Supabase Auth; the API verifies JWTs against Supabase JWKS
- **cache** — Upstash Redis (rate limiting and hot keys only)
- **ml** — frozen multilingual sentence encoder (384-dim) + FINDING user tower, PyTorch → ONNX, run offline only
- **topics** — IPTC Media Topics; concept IDs are the canonical key
- **mobile** — Expo React Native (Stage 10)
- **tooling** — `uv` for Python, `pnpm` + Turborepo for JS, Docker Compose locally

## Working agreement

- Plan before non-trivial work; get the plan approved, then build the whole slice.
- One stage at a time, in roadmap order. Nothing from a later stage leaks into
  an earlier one.
- Small, reviewable diffs. If a change touches more than ~8 files, propose a split.
- No new dependency without naming what it replaces and what removing it costs.
- Don't fix unrelated things you notice — list them.

## Code rules

- Layering: `routers/ → services/ → repositories/`. Business logic must not
  import FastAPI. Repositories must not contain business rules.
- Typed domain errors in services; HTTP status mapping only in routers.
- Every external call has an explicit timeout and a retry policy. No bare
  `except`, no silent failure.
- Every endpoint: Pydantic request and response models, plus an integration
  test against a real test database.
- **Cursor pagination only.** Offset pagination is not allowed on feeds.
- Timezone-aware UTC, ISO-8601. No naive datetimes.
- Never edit a migration that has run — write a new one.
- Explicit, boring code. No metaprogramming, no clever decorators.
- **`apps/` never imports `ml/`.** Only ONNX files and vectors cross that line.
- **No model inference in a request path** (ADR 0004).
- **Topics are stored as IPTC concept IDs, never labels.** Labels are a
  presentation-layer lookup, and the full hierarchical path is stored so the
  taxonomy can be browsed at any depth (ADR 0006).
- **Every article carries a language; every user carries chosen languages.**
  No query returns content in a language the reader did not ask for.
- **CSS uses logical properties** (`margin-inline-start`, not `margin-left`).
  RTL is not a later retrofit — Arabic must render correctly with zero
  locale-specific fixes (ADR 0005).
- All user-facing strings go through the i18n layer. No hardcoded English.

## Data & privacy rules

- **Never store full article text.** Title, snippet (≤300 chars), image URL,
  source, author, canonical link. Always link out to the publisher.
- Interaction logs record: user, item, position, timestamp, session, surface
  (`feed` | `explore` | `search` | `topic`), and **propensity** — the probability
  the policy had of showing that item, written at serve time by the policy that
  made the decision. This cannot be backfilled. Without it, offline evaluation
  is permanently biased.
- Any endpoint returning user data is authorised by owner or admin role; admin
  access is audit-logged. RLS on every user-owned table as defence in depth.
- No PII in logs. Log user IDs, never emails.
- A global audience means the **strictest applicable regime is the design
  target** — GDPR, UK GDPR, CCPA and India's DPDP all apply.

## Honesty constraint

Training implements FINDING's fine-grained interpolation and dynamic clustering
over **simulated** clients replayed from production logs. Serving is
centralised. Do not describe this as a federated production system anywhere —
README, UI, or commit message — because it is not one.

## Commands

```
make up            # local stack
make test          # uv run pytest -q  &&  pnpm test
make lint          # uv run ruff check .  &&  pnpm lint
make migrate       # uv run alembic upgrade head
pnpm --filter web dev
pnpm exec playwright test
```

## Definition of done for a slice

- [ ] Migration applies cleanly on a fresh database
- [ ] Integration test passing against real Postgres
- [ ] Error paths return the standard error envelope
- [ ] Cache policy stated for every new endpoint
- [ ] ADR written if a real decision was made
