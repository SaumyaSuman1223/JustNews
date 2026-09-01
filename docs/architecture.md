# Architecture

**Status:** proposed with the roadmap. Revise it as reality disagrees.

## Context

JustNews is a personalised news reader for a **global, multilingual audience**.
It aggregates headlines from RSS feeds, the GNews API and metadata scraping in
8–10 languages, groups near-duplicate coverage into stories — **across
languages**, since the embeddings are multilingual — classifies them against
**IPTC Media Topics**, and ranks them per user. It stores metadata only — title,
snippet, image URL, source, author, canonical link — and always links out to the
publisher. It never stores or republishes full article text.

## Services

| Service | Responsibility | Runs on | Scales on | Fails how |
|---|---|---|---|---|
| `web` | Rendering, routing, edge caching, SEO | Vercel | Requests (edge, automatic) | Falls back to cached pages; API failures render a degraded feed, never a 500 |
| `api` | Feed, search, saves, history, admin, interaction logging | Render (free tier) | Requests, scales to zero | 5xx budget; web serves cached content and a stale-data banner |
| `ingestion` | RSS polling, GNews calls, metadata scraping, dedup, classification, embedding | GitHub Actions cron, every 15 min, no deploy target | Feed count | Per-feed isolation; one dead feed cannot stall a run. Site keeps serving existing articles |
| `training` | FINDING training, clustering, ONNX export | Local / Colab / GH Actions, offline | Not user-facing | Nothing user-facing breaks; the last good model version stays live |
| `db` | Everything durable + pgvector + auth + storage | Supabase (same region as `api`) | Vertically only, on the free tier | Hard dependency. This is the single point of failure and we accept that at this scale |

## Data flow

**1. An article enters the system**
`ingestion` polls a feed (conditional GET) → normalise → canonicalise the URL →
detect language → embed with the **frozen multilingual encoder** → dedup
(URL → SimHash → embedding cosine, cross-lingual by construction) → attach to a
story cluster or open a new one → map or classify to an IPTC concept → write
article row + 384-dim `halfvec` embedding.

Note the reordering against a conventional pipeline: embedding happens *before*
dedup, because the multilingual vector is what makes cross-lingual clustering
possible in the first place.

**2. A user opens the feed**
`web` (RSC) calls `api /feed` with a cursor → `api` builds a candidate set
(recent, in the user's **languages**, in the user's IPTC topics, not already
seen, cluster-deduped) → ranks it by
dot product against the user vector plus recency/popularity/diversity terms →
reserves ~10% of slots for exploration → **writes an impression event per card
with its position and propensity** → returns the page + the next cursor.

**3. A click is recorded**
`web` fires an interaction event → `api` appends to `interactions` → the row
carries user, item, position, session, surface, timestamp, dwell and propensity.
Nothing about the response depends on this write.

**4. A training round runs**
Offline: interaction logs are replayed as simulated clients → FINDING runs its
interpolation and dynamic clustering → both towers export to ONNX → the new
model version is registered → article embeddings are recomputed in the
background → user vectors and group assignments refresh → the admin console
can promote or roll back the version.

## Why it is split this way

**`web` / `api`.** If they were one service, every page render would be
CPU-bound on the API host and we would burn its free compute budget on HTML.
Separating them lets Vercel's edge cache absorb the read traffic — which is
almost all traffic on a news site — while the API handles only personalised and
mutating calls.

**`api` / `ingestion`.** Ingestion is bursty, slow, and fails constantly in
normal operation: feeds go down, hosts rate-limit, pages fail to parse. Fused
into the API those failures would consume request-serving capacity and blur the
error budget. Split, a catastrophic ingestion run is invisible to readers — the
site just stops getting newer.

**`api` / `training`.** Different languages of correctness. Research code
optimises for iteration speed and is allowed to be ugly; product code is not.
The boundary is enforced mechanically: `apps/` must never import `ml/`. The only
things that cross are ONNX files and vectors.

**Model / request path.** See `docs/decisions/0004-no-inference-in-hot-path.md`.
The two-tower structure means both encoders run offline, so a feed request is a
database query. This is the decision the whole free-tier latency story rests on.

**Edge / origin.** The API's free-tier region is in the US, and the audience
is global — a reader in Delhi is ~230 ms from the origin before it does any work.
So the boundary is drawn by cacheability, not by feature: everything anonymous or
cacheable (home, topic pages, story pages, articles) renders on Vercel and is
served from the edge PoP nearest the reader, and the personalised path is reduced
to one round trip per session with client-side pagination from a prefetched
buffer. Impression and click writes are fire-and-forget and never block a render.
This is the largest single latency item in the system and it is structural, not
tunable. See ADR 0003 and ADR 0005.

## Degraded modes

| Down | What still works |
|---|---|
| `api` | Cached feed and article pages from the edge; a banner says content may be stale; auth-only surfaces show a friendly error |
| Ranking / user vectors stale or missing | Heuristic ranker (recency × IPTC topic affinity × popularity × language match); the feed is still good, just less personal |
| `ingestion` | Everything, with no new articles. Admin sees the failed run; users see a "last updated" timestamp |
| GNews quota exhausted | RSS covers the majority of the corpus; only long-tail topic backfill suffers |
| Supabase | Nothing. Documented and accepted. Migration to a replica-capable Postgres is a Stage 11 item |
