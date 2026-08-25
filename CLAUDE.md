# CLAUDE.md

Guardrails for AI-assisted work in this repo. Read this at the start of every
session. The point of this project is that the author learns the system, not
that the system gets built fast.

## Project

A personalised news reader. Ranking uses clustered, interpolated
personalisation derived from FINDING (CIKM '23). Training runs over simulated
clients replayed from production logs; serving is centralised. Never describe
this as federated production serving.

## Stack

- **api** — FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2 async, Alembic
- **db** — PostgreSQL 16 + pgvector
- **cache/queue** — Redis, Celery (or arq)
- **inference** — PyTorch → ONNX Runtime
- **web** — Next.js App Router, TypeScript, TanStack Query, Tailwind
- **mobile** — Expo React Native
- **tooling** — `uv` for Python, `pnpm` + Turborepo for JS, Docker Compose locally
- **infra** — Terraform (Azure first, AWS later)

## How to work with me

1. **Plan before code.** Default to a plan. When I ask a design question,
   give 3 options with trade-offs and failure modes, recommend one, and stop.
   No code until I say "go".
2. **One vertical slice per session.** One endpoint plus its model, migration,
   test, and UI. Then stop so I can review. Do not continue to the next slice
   unprompted.
3. **Every code response ends with three sections:**
   - *Assumptions I made*
   - *What I did not handle*
   - *Two most likely ways this breaks in production*
4. **I write the tests.** When I ask for an implementation, do not also write
   the test unless I say so. If I give you a failing test, make it pass
   without changing the test.
5. **No new dependency without asking.** Name it, say what it replaces, and
   what removing it later would cost.
6. **Explain on request, not by default.** Don't prefix answers with summaries
   of what I asked.
7. **Small diffs.** If a change touches more than ~5 files, stop and propose
   a split first.
8. **Don't fix unrelated things you notice.** List them; I'll decide.

## Code rules

- Layering: `routers/` → `services/` → `repositories/`. Business logic must
  not import FastAPI. Repositories must not contain business rules.
- Raise typed domain errors in services; map to HTTP status only in routers.
- Every external call gets an explicit timeout and a retry policy. No bare
  `except`. No silent failure.
- Every endpoint: Pydantic request and response models, plus at least one
  integration test hitting a real test database.
- Pagination is cursor-based. Offset pagination is not allowed on feeds.
- All money/time in UTC, ISO-8601, timezone-aware. No naive datetimes.
- Never edit a migration that has already run — write a new one.
- Prefer explicit, boring code. No metaprogramming, no clever decorators, no
  dynamic attribute access.
- `ml/` is never imported by `apps/`. Research code and product code have
  different standards.
- Never store full article text from a publisher. Title, snippet, image URL,
  source, canonical link only.

## Data & privacy rules

- Interaction logs must record: user, item, position, timestamp, session,
  surface (feed | explore | search), and **propensity** (the probability the
  policy had of showing that item). Propensity logging is mandatory — without
  it, offline evaluation is biased and unfixable retroactively.
- Any endpoint returning user data must be authorised by owner or admin role;
  admin access is audit-logged.
- No PII in logs. Log user IDs, never emails.

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

- [ ] Migration written and applied cleanly on a fresh database
- [ ] Integration test passing against real Postgres
- [ ] Error paths return the standard error envelope
- [ ] I read the whole diff with `git add -p` and can explain every hunk
- [ ] ADR written if a real decision was made
