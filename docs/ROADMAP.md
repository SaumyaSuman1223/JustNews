# JustNews — Delivery Roadmap

**Status:** proposed (revision 2), awaiting review
**Date:** 2026-09-01
**Owner:** Saumya Suman

A personalised news reader with the polish of a major publisher's site, for a
**global, multilingual audience**, ranking derived from **FINDING**
(Yu et al., CIKM '23), deployed entirely on free tiers.

**Revision 2 changes**, from your answers: personalisation ships **before**
public launch; the audience is **global**; **no comments**; topics use the
**IPTC Media Topics** taxonomy.

---

## 1. Decisions locked

| Area | Choice | Why |
|---|---|---|
| Web | **Next.js (App Router) on Vercel** | RSC + edge caching gives the fastest first paint for a read-heavy site, free Hobby tier, preview deploys per PR. Vercel's multi-region edge is now doing more work than before — see §4 |
| API | **FastAPI on Render** (free tier) | No cloud account or Terraform state to stand up — deploys on push to `main` via Render's own git integration, portable Docker either way. See ADR 0010 |
| Database | **Supabase Postgres 17 + pgvector**, same region as the API | Postgres we would have chosen anyway, plus vector search, auth and storage in one free project |
| Auth | **Supabase Auth** | OAuth, verification, reset, MFA — solved, in a dozen locales already |
| Taxonomy | **IPTC Media Topics** | 17 top-level concepts, 1,200+ terms over 5 levels, official translations in 13 languages. The multilingual part is why it wins outright now the audience is global |
| Cache / rate limit | **Upstash Redis** + HTTP cache headers | The CDN does the caching; Redis does rate limits and hot keys only |
| Scheduled work | **GitHub Actions cron**, running the ingestion CLI directly | No always-on worker needed on any tier; the cron also keeps Supabase from auto-pausing |
| News encoder | **Frozen multilingual sentence encoder** (384-dim) | The decision that makes a global corpus tractable — see §3 and ADR 0005 |
| Ranker | **FINDING user tower + dynamic clustering**, trained offline | The paper's actual contribution lives in the training procedure, not the news tower |
| Mobile | **Expo React Native** (Stage 10) | Reuses `packages/api-client` and `packages/schemas` verbatim |

Dropped from the original scaffold: **Celery** (no always-on worker on a free
tier), the **Azure** Terraform path, and — per your answer — **comments**.

---

## 2. The dependency that reorders everything

You asked for personalisation before launch. There is a catch worth stating
plainly, because it changes the shape of the plan rather than just its order.

**FINDING trains on replayed interaction logs. You cannot have interaction logs
before you have users.** A model trained on an empty database is not a model.
So "personalisation before public launch" cannot mean "no users until the model
is done" — that is circular.

The resolution is a **private beta** partway through:

```
Stage 4 ends  →  PRIVATE BETA  →  invited users read a real site
                                  the heuristic ranker serves them
                                  every impression logs position + propensity
                                       ↓  weeks of real logs accumulate
Stage 6       →  FINDING pretrains on MIND-small (public, English)
                 then adapts on your own beta logs
Stage 8       →  PUBLIC LAUNCH, personalisation live
```

The beta is a working, deployed, invite-only news site — not a prototype. It
does three jobs at once: it generates the training data Stage 6 needs, it
proves the product before strangers see it, and it means the heuristic ranker
in Stage 5 is validated against real behaviour rather than your own guesses.

**Be honest about scale.** FINDING's dynamic clustering groups users by their
learned vectors. With a few dozen beta users there are no meaningful groups, and
`num_groups=8` on 40 users is numerology. Stage 6 therefore ships in two parts:
the model architecture and pipeline validated on MIND-small (where the paper's
numbers are reproducible), then progressively adapted on real logs as volume
allows. If beta volume stays small, the honest outcome is a personalised
*user-tower* ranker without meaningful group structure — still better than the
heuristic, and the group mechanism switches on later when the numbers justify
it. That result gets recorded, not hidden.

The second consequence of reordering: **deployment moves to Stage 0.** If a beta
is live from Stage 4, the deploy pipeline cannot be a stage near the end. From
week one, `main` deploys to a real staging environment on real infrastructure.
This is a better plan regardless of your answer — deferred deployment is where
projects go to die.

---

## 3. The two ideas the system rests on

### 3.1 No model inference inside a user request

NRMS is a *two-tower* model. The news tower and the user tower are independent,
and their outputs only ever meet in a dot product. So both run **offline**:

```
ingest time   →  news encoder  →  article vector  →  stored in pgvector
nightly/async →  user encoder  →  user vector     →  stored on the user row
request time  →  ANN search + dot product + rerank  →  pure SQL + a little Python
```

- A `/feed` request costs a Postgres query, not a forward pass. p95 **< 200 ms**
  is realistic on a free tier; with ONNX in the loop it is not.
- Cloud Run's 180,000 free vCPU-seconds/month stop being the binding constraint.
- Models upgrade, promote and roll back without an API deploy.
- Missing or stale vectors fall back to the heuristic ranker, and the feed is
  still good.

Full write-up: `docs/decisions/0004-no-inference-in-hot-path.md`.

### 3.2 A frozen multilingual news encoder

This one is new in revision 2, and it is forced by "global".

FINDING's news encoder is NRMS over **GloVe 300d English word vectors**. It
cannot read Hindi, Arabic, or Spanish. A global corpus breaks it on contact.

The fix is to notice *where the paper's contribution actually lives*. FINDING's
novelty is the fine-grained interpolation coefficient and the dynamic clustering
of user models — both properties of the **training procedure and the user
tower**. The news tower is ordinary NRMS, and is replaceable.

So: **freeze a multilingual sentence encoder as the news tower** (384-dim,
covering 50+ languages), and keep FINDING's trainable user tower and training
loop on top of it. Three things fall out:

1. The corpus becomes language-agnostic, and articles in different languages
   land in one shared vector space — which means cross-lingual recommendation
   works for free, and a user vector built from English reading can surface a
   relevant Spanish article.
2. Because the news encoder is frozen, **article vectors never need
   recomputing** when the ranker is retrained. On a 500 MB database with a batch
   re-embed job that would otherwise run on every model upgrade, this is a large
   operational win.
3. 384 dimensions as `halfvec` is 768 bytes per article — half of what a
   1536-dim embedding would cost against the storage budget.

The cost, stated honestly: we no longer reproduce FINDING's exact numbers,
because the news encoder differs. Stage 6 therefore reproduces the paper
faithfully on MIND-small *first* — original GloVe news tower and all — as the
validation that the port is correct, and only then swaps the tower for
production. Both results get written down.

Full write-up: `docs/decisions/0005-global-multilingual.md`.

---

## 4. Hard constraints we are designing against

Measured limits, verified September 2026.

| Limit | Value | What it forces |
|---|---|---|
| GNews free tier | 100 req/day, 10 articles/req, **12-hour delay**, non-commercial | GNews cannot be primary. RSS is primary; GNews backfills search and thin languages |
| Supabase free DB | 500 MB | 90-day retention, `halfvec` embeddings, monthly interaction rollups. Budget ≈ 3 KB/article |
| Supabase free | pauses after **7 days** with no DB traffic | The 15-minute ingestion cron is also the keep-alive. Non-negotiable |
| Cloud Run always-free | 2M req/mo, 180k vCPU-s, **US regions only** | **The sharpest constraint now the audience is global.** See below |
| Vercel Hobby | non-commercial | Migration path is Cloudflare Pages or self-hosted Next.js on Cloud Run |
| IPTC Media Topics | 13 languages | Covers most of Europe, Arabic and Chinese. **No Hindi or other Indian languages** — those need our own labels |
| Publisher copyright | — | Title, snippet ≤ 300 chars, image URL, source, author, canonical link. **Never full text.** Always link out |

**On the US-only free region, given a global audience.** A reader in Delhi is
~230 ms from `us-east1` before the API does any work. That is the single
largest latency item in the system and no amount of query tuning touches it.
The mitigations, in the order we apply them:

1. **Anonymous and cacheable routes never reach Cloud Run.** Home, topic pages,
   story pages and article pages render on Vercel with ISR and are served from
   the edge PoP nearest the reader. For a news site this is the large majority
   of pageviews.
2. **The personalised feed is fetched once per session, then paginated
   client-side** from a prefetched buffer, so the transcontinental round trip
   happens once rather than per scroll.
3. **Writes are fire-and-forget.** Impression and click logging never blocks a
   render.
4. **Measured, not assumed.** Stage 8 instruments real-user latency by region.
   If p75 outside North America stays poor, the answer is a paid regional API
   instance, costed in Stage 11 — not a redesign.

---

## 5. The stages

Twelve stages, three arcs. **Arc I** builds a working site and puts it in front
of invited users. **Arc II** makes it personal, using the data Arc I produced.
**Arc III** launches it publicly and grows it.

---

### Arc I — Build the newspaper *(→ private beta)*

#### Stage 0 · Foundations & continuous deployment
*Estimate: 1.5 weeks*

Everything boring, plus a deploy pipeline from day one because a beta is live
from Stage 4.

- `uv` workspace for Python, `pnpm` + Turborepo for JS.
- Docker Compose: Postgres 17 + pgvector, Redis, api, web; Supabase CLI for
  local auth parity.
- CI under 90 s: ruff, mypy, pytest, eslint, tsc, a Playwright smoke test.
- **A real staging environment, and `main` → staging deploy working before
  any product code exists**, on Render (API) and Vercel (web) — both deploy
  on push to `main` via their own git integration, no custom deploy workflow
  needed. Secrets live in each platform's own dashboard and in GitHub
  Actions secrets for the ingestion cron (ADR 0010).
- Error-envelope, structured logging and request-ID conventions.
- ADRs 0001 (stack), 0003 (free-tier deployment), 0004 (no inference in hot
  path), 0005 (global/multilingual), 0006 (IPTC taxonomy).

**Done when:** a fresh clone reaches a running stack in under five minutes using
only the README, CI is green on a PR, and a merge to `main` visibly deploys a
`/health` endpoint to staging.

---

#### Stage 1 · Multilingual content pipeline
*Estimate: 2 weeks*

The stage that decides whether this feels like a real news site. Stale,
duplicated or badly-categorised articles cannot be rescued by good ranking.

- **Schema:** `sources`, `feeds`, `articles`, `story_clusters`, `topics` (IPTC),
  `article_topics`, `authors`, `editions`, `ingest_runs`.
- **RSS ingestion (primary):** 250–400 curated feeds across ~17 IPTC top-level
  topics, **8–10 launch languages** and a set of regional editions.
  Conditional GETs, per-feed backoff, one dead feed never stalls a run.
- **Language detection** at ingest, stored per article; readers see only the
  languages they have chosen.
- **GNews (secondary):** topic and language backfill inside a 100-call daily
  budget, spent where RSS coverage is thin — which for a global corpus is
  usually the non-English long tail.
- **Enrichment scraping:** canonical URL, OG image, author, published time —
  metadata only, `robots.txt` respected, per-host rate limits, identifying
  User-Agent.
- **Deduplication, three layers:** URL canonicalisation → SimHash on
  title+snippet → embedding cosine within a time window. Near-duplicates group
  into a **story cluster**, so the feed shows one story rather than eight
  versions of the same wire copy. Because embeddings are multilingual, the same
  story reported in three languages clusters together — a genuinely nice
  property that mono-lingual aggregators do not have.
- **IPTC classification:** map each source's own categories to IPTC where a
  mapping exists, classify the rest. Store the full IPTC path so the taxonomy
  can be browsed at any depth.
- **Search:** Postgres `tsvector` with per-language configurations, plus
  `pg_trgm`. Hybrid with pgvector later.
- **Retention:** 90-day hot window, then prune.

**Done when:** 8,000+ live articles across at least 6 languages, deduped into
cross-lingual story clusters, IPTC-tagged, refreshing every 15 minutes, with
search returning sensible results in each language.

---

#### Stage 2 · API core + auth
*Estimate: 1.5 weeks*

- FastAPI, layered `routers/ → services/ → repositories/`. Business logic never
  imports FastAPI.
- Supabase JWT verification via JWKS; RLS on every user-owned table as defence
  in depth.
- Endpoints: `/feed`, `/articles/{id}`, `/stories/{id}`, `/topics`, `/search`,
  `/saves`, `/history`, `/not-interested`, `/follows`, `/me`, `/health`.
- **Cursor pagination everywhere.** Never offset, on any feed.
- **Interaction logging designed now.** Every impression records user, item,
  position, session, surface (`feed | explore | search | topic`), locale,
  timestamp, and **propensity** — the probability the policy had of showing that
  item, written at serve time by the policy that made the decision. It cannot be
  backfilled. Without it, Stage 6's offline evaluation is permanently biased.
- Standard error envelope, request IDs, rate limiting, OpenAPI → generated typed
  TS client with a CI drift check.
- Explicit degraded modes: ranker down → chronological; search down → topic
  browse; DB slow → cached page.

**Done when:** p95 on a warm `/feed` is under 200 ms measured from the same
region, every endpoint has an integration test against real Postgres, and the
typed client is generated in CI.

---

#### Stage 3 · Web app, internationalised from the start
*Estimate: 3 weeks — the largest single stage*

Where it stops looking like a side project. Visual direction is specified in
`docs/design/design-system.md`.

- **Design system:** a type scale built for long-form reading, an 8pt grid, one
  accent colour, light and dark as first-class peers, and a fixed set of card
  sizes so any feed the ranker produces still composes.
- **i18n is structural, not a later retrofit.** Locale-segmented routing,
  translated UI chrome, **RTL layout for Arabic and Hebrew** (logical CSS
  properties throughout, not `left`/`right`), locale-aware dates, numbers and
  relative times, per-locale font stacks with correct script coverage, and a
  language/edition switcher that is a first-class control rather than a footer
  link. Retrofitting RTL into a finished layout costs several times what
  building with logical properties costs; that is why this is here and not in
  Stage 11.
- **Routes:** home feed, IPTC topic pages at multiple depths, edition and
  language pages, story page (a cluster of coverage across sources and
  languages), article reader, search with filters, saved, history, settings,
  onboarding, auth, publisher/source pages, about/legal, 404/500, offline.
- **Performance budget:** LCP < 1.5 s, INP < 200 ms, CLS < 0.1, JS < 150 KB
  gzipped on the article route — measured on a throttled mid-range phone, not a
  laptop.
- **Accessibility:** WCAG 2.2 AA, axe-clean in CI, keyboard-navigable end to
  end, `prefers-reduced-motion` honoured.
- **PWA:** installable, saved articles readable offline.
- SEO groundwork: `hreflang` across locales, canonicals, `NewsArticle` JSON-LD,
  OG images.

**Done when:** Lighthouse ≥ 95 on performance, accessibility, best practices and
SEO for the feed and article routes on a throttled mobile profile; the site is
fully usable with the keyboard alone; and the Arabic locale renders correctly
right-to-left without a single layout fix specific to it.

---

#### Stage 4 · Publisher & ops layer → **private beta**
*Estimate: 1.5 weeks*

The half of a news company's software the public never sees. It comes before
personalisation because you cannot tune a ranker you cannot measure.

- **Admin console** (role-gated, every action audit-logged): source and feed
  management with health indicators and per-language coverage, ingestion run
  monitor, article moderation and takedown, IPTC taxonomy browser and override
  editor, user and role admin, feature flags.
- **Analytics:** DAU/WAU, CTR by surface and position, dwell distribution,
  scroll depth, retention cohorts, top stories, source performance — **sliced by
  locale and language**, which is the only way a global product tells you
  anything useful.
- **Experiment console:** variant assignment, exposure logging, guardrail
  metrics. Built now because every stage from 5 onward is meaningless without it.
- **Distribution:** sitemap index per locale, news sitemaps, outbound RSS,
  structured-data validation in CI.
- **Observability:** structured JSON logs, Sentry, uptime checks, and a runbook
  filled in as things actually break.
- **Compliance, global scope:** consent management that satisfies GDPR *and* UK
  GDPR, CCPA and India's DPDP; a privacy policy; data export and account
  deletion; a documented retention policy. A global audience means the strictest
  applicable regime is the design target.
- **Beta gate:** invite codes, a feedback widget, and a way to watch a single
  user's session from the admin side while debugging.

**Done when:** you can operate the site for a week — add sources, fix bad
categorisation, take an article down, read yesterday's numbers by locale —
without opening a SQL client. **Then invite the first beta users.**

### ▶ PRIVATE BETA OPENS

---

### Arc II — Make it personal *(on data the beta produced)*

#### Stage 5 · Personalisation v1 — heuristic
*Estimate: 1 week*

A strong non-ML baseline that serves the beta and generates the propensity-logged
impressions Stage 6 trains on. Stage 6 has to beat this, and it is harder to
beat than people expect.

- Onboarding: language and edition selection, then an **IPTC topic picker at the
  top two levels** — 17 concepts, expandable, not 1,200.
- Ranker: recency decay × IPTC topic affinity × popularity × source trust ×
  language match, minus penalties for already-seen, already-clustered, and
  "not interested".
- **Diversity via MMR** over both topic and source, so the feed never collapses.
- A/B harness proving it against a chronological control.

**Done when:** the personalised feed beats chronological on CTR among beta users,
with the result recorded in the experiment console.

---

#### Stage 6 · The FINDING model
*Estimate: 4 weeks — the research core*

Two parts, and the order matters.

**Part A — reproduce the paper faithfully.** Port and run the original repo
(`resources/FINDING`) on MIND-small with its original GloVe news encoder. Record
every dependency change in `ml/finding/PORTING-NOTES.md`. Own the metrics —
nDCG@5/@10, MRR, AUC — implemented and unit-tested against hand calculations
before trusting anyone's numbers, yours or theirs. Locate and understand the two
mechanisms that make the paper the paper: the fine-grained interpolation
coefficient `λ(t,i) = (1 − α^−t)·((i+1)/N)^β` and the transition-matrix remix of
group models after re-clustering. **This part is the proof the port is correct**,
and it is not skippable — everything afterwards is uninterpretable without it.

**Part B — adapt it to a global product.** Swap the news tower for the frozen
multilingual sentence encoder (§3.2), keep FINDING's user tower and training
loop, and retrain on **simulated clients replayed from beta interaction logs** —
which is why Stage 2's propensity logging had to be right. Export the user tower
to ONNX with a parity test against PyTorch. Wire into the offline pipeline: news
vectors at ingest, user vectors nightly plus on demand for active users, group
centroids stored and versioned with the model.

**Evaluation:** offline with IPS / doubly-robust estimators over the logged
propensities, then shadow mode against live traffic, then a live A/B against
Stage 5.

**Honesty constraint, carried into every public description:** training
implements FINDING's interpolation and dynamic clustering over *simulated*
clients replayed from production logs. Serving is centralised. This is not a
federated production system, and the README, the UI and your CV must not say
that it is.

**Done when:** Part A reproduces the paper's MIND-small numbers within a
documented tolerance, and Part B's ranker beats the Stage 5 heuristic offline on
nDCG@10 and then online on CTR — with model versions rollback-able from the
admin console. If beta volume is too small for meaningful group structure, that
is recorded as the result and the group mechanism is deferred, not faked.

---

#### Stage 7 · Exploration deck — cold start
*Estimate: 1.5 weeks — your differentiator*

Your original idea, built properly: infer interests from what people do, not
from what they say they like.

- A stratified deck of ~20 cards: sampled per IPTC top-level topic, then
  popularity-weighted within topic, positions randomised, capped so no topic
  dominates. Filtered to the reader's languages.
- Signals and weights: click (strong +), long dwell without click (weak +),
  save or share (strong +), fast scroll-past (weak −), explicit not-interested
  (strong −). Position is logged and corrected for.
- Thompson sampling over topic arms with a popularity prior — honestly evaluated
  against ε-greedy, given only ~20 pulls across 17 arms.
- Skippable at any point; degrades to popularity within picked topics.
- **The handoff:** run the user tower over engaged articles → user vector →
  assign to the nearest FINDING group centroid. Exactly how the paper handles
  users who exist only at evaluation time, shipped as a product feature.
- **Exploration never stops:** a permanent ~10% slice of every feed page stays
  exploratory, or the feedback loop closes and the filter bubble becomes
  structural.

**Done when:** a brand-new account that goes through the deck gets a visibly
different feed from one that skips it — and you can show, from the interaction
log, exactly why.

---

### Arc III — Launch and grow

#### Stage 8 · Global public launch
*Estimate: 1.5 weeks*

- Real-user monitoring by region and locale; act on the latency data rather than
  the assumption.
- Load test the free tier honestly and write down where it breaks.
- Production environment cut over from beta; custom domain, TLS, security
  headers, CSP; a rollback you have personally executed.
- Restore drill: destroy staging's data and bring it back from backup.
- Launch checklist: legal pages per jurisdiction, consent flows verified in the
  EU, sitemaps submitted, `hreflang` validated, abuse and takedown contact live.

**Done when:** merging to `main` ships to production unattended, a real domain
serves a personalised, multilingual site to the public, and you have executed a
rollback for real.

### ▶ PUBLIC LAUNCH GATE

---

#### Stage 9 · Engagement layer
*Estimate: 1.5 weeks*

Web push and breaking-news alerts (locale-aware, sent at a sensible local hour),
email digest, follow topics, sources and authors, trending and most-read rails,
live blogs, newsletter signup. **No comments** — per your answer; the moderation
liability across jurisdictions and languages is not worth it at this size.

#### Stage 10 · Mobile app
*Estimate: 3 weeks*

Expo React Native reusing `packages/api-client` and `packages/schemas`
unchanged. Push notifications, offline reading, deep links, share extension,
RTL support inherited from the design system, EAS build on the free tier, store
submission.

#### Stage 11 · Hardening & scale
*Estimate: 1 week, ongoing*

Load testing, a costed model of 10× and 100× traffic, the documented migration
path off each free tier, a costed decision on a paid regional API instance if
the latency data demands it, an adversarial security review, backup and restore
drills, and a retention job that actually runs.

---

## 6. Timeline

| Arc | Stages | Estimate | Milestone |
|---|---|---|---|
| I — Build the newspaper | 0–4 | ~9.5 weeks | **Private beta** |
| II — Make it personal | 5–7 | ~6.5 weeks | Personalisation live in beta |
| III — Launch and grow | 8 | ~1.5 weeks | **Public launch** — week ~17.5 |
| | 9–11 | ~5.5 weeks | Engagement, mobile, hardening |

**~17.5 weeks to public launch**, against ~9 in revision 1. The extra eight
weeks buy three things: a launch that includes real personalisation, a global
multilingual product rather than an English one, and a beta period that de-risks
all of it. **A working site is in front of real users at week 9.5** — the
private beta is the thing that keeps this from being four months of silence.

If that is too long, the lever is Stage 6. Shipping with the Stage 5 heuristic
ranker and treating FINDING as a post-launch upgrade recovers four weeks and
still launches a personalised product.

---

## 7. Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Beta produces too little data to train FINDING | **High** | Pretrain on MIND-small; adapt progressively; ship the user tower without group structure if volume demands, and record that honestly |
| Global latency from a US-only free region | **High** | Edge-render everything cacheable; one personalised round trip per session; measure by region in Stage 8; cost a paid regional instance in Stage 11 |
| i18n/RTL retrofitted instead of built in | **High** | Logical CSS properties from the first component in Stage 3; Arabic in the Stage 3 done-criteria |
| Supabase 500 MB fills up | High | 90-day retention, `halfvec` at 384 dims, monthly rollups, alert at 70% |
| Supabase auto-pauses | High | 15-minute ingestion cron doubles as keep-alive; uptime check alerts on pause |
| Scope creep | High | The stage gates. Nothing from a later stage enters an earlier one |
| GNews 12-hour delay makes the site feel stale | Medium | RSS is primary and near-real-time; GNews only backfills |
| Multilingual encoder underperforms GloVe NRMS on English | Medium | Stage 6 Part A measures exactly this on MIND-small before Part B commits |
| IPTC has no Hindi or Indian-language labels | Medium | Use IPTC concept IDs as the canonical key and supply our own display translations for uncovered languages |
| Cold-start feedback loop / filter bubble | Medium | Permanent 10% exploration slice; diversity term over topic *and* source; measured, not assumed |
| Publisher copyright complaint | Medium | Metadata only, prominent attribution, always link out, takedown tooling in Stage 4 |
| FINDING fails to beat the heuristic | Medium | A legitimate result — record it. The heuristic ranker still ships |

---

## 8. Still open

1. **Domain name.** Needed by Stage 8, but worth registering early — it affects
   the `hreflang` and locale-routing strategy in Stage 3 (subdirectories like
   `/es/` versus subdomains).
2. **Launch languages.** Which 8–10? The IPTC-covered set (English, Spanish,
   French, German, Portuguese, Arabic, Chinese, Danish, Norwegian, Swedish) is
   the cheapest start. Adding Hindi is entirely reasonable but means supplying
   our own topic labels.
3. **Beta size and recruitment.** Roughly how many invited readers can you
   realistically get, and from where? This is the single number that decides
   whether Stage 6's group clustering is meaningful or theatre.
