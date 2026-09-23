**Title:** JustNews: Stages 1–9 web product, Aquila, My Desk, and the fifth UX pass

## Summary

`main` has only the initial commit, so this PR brings in the whole product
built on `chore/scaffold`, which is 158 commits. It is large because the
branch was never merged in slices. Each commit is scoped and reviewable on
its own.

**Foundation**
- A monorepo:
  - `backend/` (FastAPI, SQLAlchemy 2 async, Alembic)
  - `frontend/` (Next.js App Router, i18n en/es/hi, RTL-safe logical CSS)
  - `apps/ingestion/` (RSS + GNews, dedup, story clustering)
  - `ml/` (offline only)
  - `mobile/` (Expo)
- Supabase Auth with JWKS verification and RLS on every user-owned table.
- The API deploys to Render and the web app to Vercel (ADR 0010). Ingestion
  runs as a scheduled GitHub Actions job.
- Uptime monitoring is included.

**Product**
- A ranked, cursor-paginated personal feed. Propensity is logged at serve
  time.
- Explore and the exploration deck.
- Search with filters.
- Saves, history, the reading profile, data export and account deletion.
- A consent gate.

**Three destinations (ADRs 0011–0013)**
- Home, as a briefing.
- The Aquila Tribune: precomputed issues three times a day, readable as a
  paged newspaper.
- My Desk: a topic workspace with a timeline, key developments, and
  Perspectives grouped by the publisher's source role.

**Fifth pass: fixing what real data broke** (see `docs/FIFTH_PASS_PLAN.md`)
1. Ingestion skips programme and podcast episodes. The dedup window is now
   bounded between the two articles being compared.
2. Empty states are honest. Topic pages fall back to real reporting, and the
   Analysis stub is gone.
3. Aquila fits a real edition: the masthead was cut from 250px to 99px, and
   the lead now always sits inside the sheet.
4. Home's "What matters" is earned. The new `/v1/articles/top` ranks by
   recency × breadth of coverage × source trust. Repeats are gone, and so are
   the hydration failures.
5. Publisher pages at `/source/[slug]`. The article page now leads to "Filed
   under", "More in {topic}" and "More from {source}".
6. Search shows one row per story, marks the query words, and suggests topics
   and publishers as you type.
7. Follow a story (migration 0018, with RLS). Cards say when a story is
   covered in other languages, and new items since your last visit are
   marked (stored on the device only).
8. Card reasons now come from the real ranker. Also added: a Display page
   (theme and text size, with no flash), keyboard shortcuts, a "How JustNews
   works" page, and password reset.
9. Polish and QA:
   - `/v1/articles/top` went from 0.85s to 0.05s (MMR in O(n²) with an early
     stop).
   - The consent banner now dismisses on Home. It posts to `/api/consent`
     and gets a 303 back. The Server Action path it replaced never committed
     its re-render in production builds.

The ranker implements FINDING's interpolation and clustering over simulated
clients replayed from logs. Serving is centralised; this is not a federated
production system.

## Migrations

`0001` through `0018`. `0018_story_follows` was round-tripped
base → head → base → head on a scratch database.

## Test plan

- [x] `uv run pytest -q`: 539 passed, against real Postgres 17 + pgvector.
- [x] `uv run ruff check .`, `uv run mypy backend/src`, `pnpm typecheck`,
  `pnpm lint`: all clean.
- [x] `pnpm exec playwright test` on a production build: 19 passed, 3 skipped.
  The skipped specs need signed-in credentials.
- [x] `pnpm test:e2e:structured-data`: passed.
- [ ] Signed-in review against a real test account:
  - follow a story
  - card reasons
  - the reset-password landing page
  - My Desk's followed stories
  - save, follow and "not interested" on Home (these may hit the same Next
    commit bug as the old consent banner)
- [ ] After merge, confirm production ingest with the real encoder builds
  multi-source clusters. The breadth ranking, grouped search and
  other-language lines all depend on them.

## Known and not fixed

- 16% of articles have no topic, because some feeds (BBC Spanish and Hindi
  general) carry no categories.
- One order-dependent flaky test in `test_follows_api.py`. It predates the
  fifth pass.
- Mobile Home is still long, about 9,000px.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
