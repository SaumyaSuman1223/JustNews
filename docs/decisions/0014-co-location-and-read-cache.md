# 0014 — Co-locate with the database, and cache shared reads in Redis

- **Date:** 2026-09-23
- **Status:** accepted; the region move is deferred (2026-09-23) - Render stays in `oregon` and Vercel on its default region until the move is done in one step. Amended 2026-10-10 (see "What production was actually doing"): the read cache gained an in-process layer and no longer needs Upstash, and Discover and Aquila stream.

## Context

Production felt slow; locally the same pages answered in 10–60ms. Measured
from India on 2026-09-23:
- `/en` took 0.6–2.1s to first byte.
- `/en/aquila` took 2.5–3.9s.
- API `/health` took 0.4s, but every database-backed read took 1.5–1.8s.

The causes were topology and repetition, not code:

- **Every query crossed an ocean.**
  - Supabase is in Tokyo, the API ran in Render Oregon, and Vercel functions
    ran in `iad1`.
  - An Aquila page makes about five sequential queries.
- **The rate limiter opened a new HTTPS client to Upstash on every request:**
  a TCP and TLS handshake before any work.
- **Nothing shared was cached.**
  - Aquila's three calls per page load bypassed Next's fetch cache.
  - The API had no read cache.
  - Next's router cache for dynamic pages was 0s, so Back refetched.
- **A signed-in page made three to five serial auth round trips:**
  - `getSession()` (a Supabase Auth `getUser`) was called in the layout, the
    page and the feed body.
  - Each call was followed by its own `/v1/me`.
- **The free API slept after 15 idle minutes, and the 15-minute uptime ping
  lost that race.**

## Options

1. **Move the database** next to the API. This is the biggest win, but a
   Supabase region change means a new project and a data migration.
2. **Move the compute to the database, and cache what everyone shares.** This
   is cheap, and reversible file by file.
3. **Cache aggressively at the edge** (`s-maxage` on pages). Every page reads
   the session cookie, so this would need the shell rebuilt around
   client-side personalisation first.

## Decision

Option 2:
- Render `singapore` (the nearest Render region to Tokyo), Vercel `hnd1`, and
  Upstash in `ap-northeast-1`.
- A read-through cache with stale-while-revalidate (`core/cache.py`), for
  anonymous responses that log nothing: the API process's own memory first,
  then Upstash when it is configured (2026-10-10).
- Per-request dedupe of the session and the profile.
- A 30s client router cache.
- A 10-minute keep-warm ping.

### Cache policy per endpoint (ADR requirement for every new endpoint)

| Endpoint | Fresh | Stale | Why this long |
|---|---|---|---|
| `GET /v1/articles` (first page, per filter set) | 60s | 300s | A new report should appear within a minute; later cursor pages are not cached |
| `GET /v1/articles/top` | 60s | 300s | Same as the list it ranks |
| `GET /v1/trending` | 60s | 300s | Clicks move by the minute, not the second |
| `GET /v1/topics` | 600s | 3600s | Every Discover page asks for its topic menu; the list changes only when the taxonomy is seeded or an admin edits a label |
| `GET /v1/sources`, `GET /v1/editions` | 600s | 3600s | Catalogues: they change when an admin adds or retires a source, or on a seed |
| `GET /v1/across-languages` | 120s | 600s | Stories gain languages as ingest runs every 15 minutes |
| `GET /v1/stories/{id}` | 60s | 300s | A developing story gains reports quickly |
| `GET /v1/stats` | 300s | 900s | A count, not a headline |
| `GET /v1/sources/{slug}` | 300s | 900s | Publisher metadata barely changes |
| `GET /v1/issues/latest`, `GET /v1/issues` | 60s | 600s | A new edition shows within about a minute of publishing |
| web: Discover's "Today's Aquila" read of `/v1/issues/latest` (Next fetch cache) | 60s | — | It went through the typed client with no cache setting, which Next 15 never caches: one API round trip in front of every Discover page |
| `GET /v1/issues/{id}` | 600s | 3600s | A published issue never changes |
| `GET /v1/issues/{id}/pages/{n}` (unconsented) | 300s | 3600s | Frozen content; short enough that a takedown clears within minutes |
| `GET /v1/issues/{id}/pages/{n}` (consented) | not cached | — | It writes impressions whose ids the client reports clicks against |
| `GET /v1/widgets/markets` | 120s | 600s | The job that writes it runs every 15 minutes |
| `GET /v1/widgets/companies` | 300s | 1800s | Replaced once per job run |
| web `GET /api/widgets/weather` (Open-Meteo, Next fetch cache + CDN) | 1800s | 3600s | The forecast updates hourly; keyed by coordinates rounded to ~1 km |
| web `GET /api/widgets/places` (Open-Meteo geocoding) | 86400s | — | A city does not move |
| `GET /v1/feed`, `/v1/explore`, anything authenticated | not cached | — | Personal, and logs propensity at serve time; a cached ranking would log a decision no policy made |
| `GET /v1/discover` (first page; signed out, no consent, no device history, no topic picks) | 60s | 300s | The deterministic ranking is the same for every such reader; it replaces the article list on Discover (ADR 0015) |
| `GET /v1/discover` (anything else) | not cached | — | Personal, or logs impressions with the probability each placement had |
| `POST /v1/clicks`, `POST /v1/impressions/views` | not cached | — | Writes |

"Stale" is how long an expired entry may still be served while a single
request, holding a 30s Redis lock, refreshes it in the background.

## Consequences

- **The database stops being on most read paths.** The Singapore→Tokyo hop
  (~70ms) is paid by one request per entry per TTL, not by every reader.
- **Redis is never required.**
  - Unconfigured, slow (0.6s timeout) or down, every read falls back to the
    database, and every rate-limit check fails open, as before.
  - Local dev and CI run without it.
- **Staleness is bounded and stated.**
  - A takedown can survive on a cached page for up to one refresh after its
    TTL.
  - Cache keys carry a version (`KEY_VERSION`), bumped whenever a cached
    payload's shape changes.
- **Moving regions is manual.**
  - Render cannot move a service, so the Blueprint creates a new one; its env
    vars and the web app's `API_URL` must follow.
  - Upstash's database region is chosen when it is created.
- **Revisit when:**
  - Supabase moves region: re-home everything next to it.
  - Traffic makes one Upstash call per request measurable: add an
    in-process layer in front.
  - The shell no longer reads cookies on the server: edge caching becomes
    possible.

## What production was actually doing (2026-10-10)

Measured from India: `/en` and `/en/aquila` took 4-5.5s to first byte, with the API awake. Pages that call no API took 0.4s. Three causes, none of them the code this ADR added:

- **Upstash was never connected to the API.**
  - It was a deploy step that did not happen.
  - With Redis as the only cache layer, that meant no cache and no rate limit: 260 requests in 25 seconds from one address were all served.
  - Every shared read ran its queries, and each query is a round trip from Oregon to Tokyo of about 100ms: 4 to 10 per request, counting the pool's pre-ping, `BEGIN` and `ROLLBACK`.
  - `/health` answered in 0.35s after TLS; `/v1/trending` in 0.9s; `/v1/discover` in 1.5-4s.
- **Vercel's fetch cache returned no hits.**
  - `/en/search` makes only hour-long cached reads. Locally its second request takes 25ms; on Vercel it never dropped below 1.3s.
  - The cause is not visible from outside the dashboard (Observability > External APIs shows each fetch's cache status).
- **Discover awaited all nine of its reads before sending a byte**, so its first byte waited on the slowest of them, and Aquila awaited three in a row.

### What changed

- **The cache has an in-process layer.**
  - A bounded map in the API process, in front of Redis, with the same fresh and stale windows per route.
  - A hit is no round trip at all, and it needs no service to exist. One API process is its own complete cache; Upstash is now what a second process, or this one after a restart, reads instead of the database.
  - On by default in `staging` and `production`, off in `local` and in tests (`Settings.in_process_cache`), where a response outliving the write before it would only hide bugs.
  - With it on, 7 of Discover's 8 endpoints issue no SQL on a repeat call. The eighth, `/v1/topics`, had never been cached and now is, with `/v1/sources` and `/v1/editions`.
- **Rendering: Discover and Aquila stream.**
  - The shell and a skeleton go out at once (first byte in about 150ms locally against the production API). The feed arrives when its page is ranked, and the rail through its own boundary.
  - The rail's reads start beside the feed's. Starting them only after the feed was measured and dropped: the feed was no faster and the rail arrived seconds later.
  - Aquila sends its sheet and masthead, then the edition.
  - With JavaScript off the skeleton stays, because streamed content is swapped in by an inline script. The site already needed JavaScript for everything past the first page.

### What is still open

- **A quiet site is a cold site.** Every entry is dropped at the end of its stale window (6 minutes for the feed), so the first reader after a quiet spell still waits for the database, with the page streaming around the wait. A ping of `/en`, `/es` and `/hi` every 5 minutes keeps the API awake and those entries warm. GitHub's scheduler cannot be that ping: it runs this repository's 10- and 15-minute schedules every 3 to 7 hours.
- **Vercel's fetch cache.** Once the API answers shared reads from memory it matters far less: a miss costs a network hop, not a ranking.
- **The region move** is worth less than it was. It shortens each database round trip from about 100ms to about 70ms, and shared reads no longer make any. It still shortens the reader's own hop to the function.
