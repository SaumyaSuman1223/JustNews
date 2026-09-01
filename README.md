# JustNews

A personalised, **multilingual** news reader with the polish of a major
publisher's site, whose ranking layer uses clustered, interpolated
personalisation derived from **FINDING** (Yu et al., CIKM '23) — deployed
entirely on free tiers.

> **Honesty statement (keep this accurate as it is built).**
> Training implements FINDING's fine-grained interpolation and dynamic
> clustering over *simulated* clients replayed from production interaction
> logs. Serving is centralised. On-device computation is not done. Do not
> describe this as a federated production system until it is one.

## Status

See **[docs/ROADMAP.md](docs/ROADMAP.md)** for the plan of record.

**Arc I — build the newspaper**
- [x] Stage 0 — Foundations & continuous deployment
- [x] Stage 1 — Multilingual content pipeline
- [x] Stage 2 — API core + auth
- [ ] Stage 3 — Web app, internationalised from the start
- [ ] Stage 4 — Publisher & ops layer · **private beta opens**

**Arc II — make it personal**
- [ ] Stage 5 — Personalisation v1 (heuristic)
- [ ] Stage 6 — The FINDING model
- [ ] Stage 7 — Exploration deck (cold start)

**Arc III — launch and grow**
- [ ] Stage 8 — Global public launch · **launch gate**
- [ ] Stage 9 — Engagement layer
- [ ] Stage 10 — Mobile app (Expo)
- [ ] Stage 11 — Hardening & scale

## Stack

| Tier | Choice | Host |
|---|---|---|
| Web | Next.js App Router, TypeScript, Tailwind, i18n + RTL | Vercel |
| API | FastAPI, Python 3.12, SQLAlchemy 2 async | Google Cloud Run |
| Ingestion | RSS + GNews + metadata scraping, 8–10 languages | Cloud Run Job, GitHub Actions cron |
| Database | Postgres 17 + pgvector | Supabase |
| Auth | Supabase Auth (JWT verified by the API) | Supabase |
| Cache | Upstash Redis (rate limits, hot keys) | Upstash |
| Topics | IPTC Media Topics (17 top-level, 1,200+ terms) | — |
| ML | Frozen multilingual encoder + FINDING user tower, offline only | Local / Colab / Actions |
| Mobile | Expo React Native | Stage 10 |

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io), and
either Docker or nothing at all (there is a fallback for the database).

```bash
git clone https://github.com/SaumyaSuman1223/JustNews && cd JustNews
cp .env.example .env
make bootstrap          # uv sync + pnpm install
make up                 # postgres + redis + api + web, via docker
make migrate seed       # schema, then IPTC topics and ~50 feeds
make ingest             # fetch real headlines - takes about two minutes
```

Then open <http://localhost:3000>. The API is on
<http://localhost:8000/docs>.

**No working Docker daemon?** (WSL without Docker Desktop integration, for
instance.) There is a fallback that runs a real PostgreSQL with pgvector out of
a Python wheel:

```bash
make db-up              # prints the DATABASE_URL to put in .env
```

Then set `VECTOR_TYPE=vector` in `.env` - the bundled pgvector predates
`halfvec` - and run `make migrate seed ingest`, `make dev-api` and
`make dev-web` in separate terminals.

### Check it worked

```bash
make stats                                  # corpus size, languages, quota
curl localhost:8000/health/ready            # {"status":"ready",...}
curl "localhost:8000/v1/articles?languages=ar&page_size=3"
```

`http://localhost:3000/ar` should render right-to-left with Arabic headlines.
If it does, ingestion, the multilingual pipeline and the i18n layer are all
working.

## Docs

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the plan of record: 12 stages, constraints, risks
- [`docs/architecture.md`](docs/architecture.md) — the system and why it's shaped this way
- [`docs/design/design-system.md`](docs/design/design-system.md) — visual direction and non-negotiables
- [`docs/runbook.md`](docs/runbook.md) — how to operate it when it breaks
- [`docs/decisions/`](docs/decisions/) — architecture decision records
- [`CLAUDE.md`](CLAUDE.md) — how AI assistance is used here

### Key decisions

- [0001](docs/decisions/0001-stack.md) — the stack, and the two stacks rejected
- [0002](docs/decisions/0002-cold-start-exploration.md) — cold start by exploration, not just a topic picker
- [0003](docs/decisions/0003-free-tier-deployment.md) — designing around free-tier limits instead of budgeting against them
- [0004](docs/decisions/0004-no-inference-in-hot-path.md) — no model inference inside a user request
- [0005](docs/decisions/0005-global-multilingual.md) — a global audience, and what it does to the model
- [0006](docs/decisions/0006-iptc-taxonomy.md) — IPTC Media Topics as the topic taxonomy
- [0007](docs/decisions/0007-auth-and-rls.md) — application-verified JWTs, and RLS keyed off a session GUC
- [0008](docs/decisions/0008-beta-gate-and-admin-rls.md) — a beta gate separate from sign-in, and an RLS bypass for admin
- [0009](docs/decisions/0009-ranked-feed-pagination.md) — a frozen-window cursor for the ranked feed

## Content policy

JustNews stores headline metadata only — title, snippet, image URL, source,
author, canonical link — and always links out to the publisher. It never stores
or republishes full article text.

## Attribution

Based on ideas from *Federated News Recommendation with Fine-grained
Interpolation and Dynamic Clustering* (CIKM '23) —
https://github.com/yusanshi/FINDING
Check that repository's licence before publishing derived code.
