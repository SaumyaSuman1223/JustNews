# 0014 — Co-locate with the database, and cache shared reads in Redis

- **Date:** 2026-09-23
- **Status:** accepted

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
- A read-through Redis cache with stale-while-revalidate
  (`core/cache.py`), for anonymous responses that log nothing.
- Per-request dedupe of the session and the profile.
- A 30s client router cache.
- A 10-minute keep-warm ping.

### Cache policy per endpoint (ADR requirement for every new endpoint)

| Endpoint | Fresh | Stale | Why this long |
|---|---|---|---|
| `GET /v1/articles` (first page, per filter set) | 60s | 300s | A new report should appear within a minute; later cursor pages are not cached |
| `GET /v1/articles/top` | 60s | 300s | Same as the list it ranks |
| `GET /v1/trending` | 60s | 300s | Clicks move by the minute, not the second |
| `GET /v1/stories/{id}` | 60s | 300s | A developing story gains reports quickly |
| `GET /v1/stats` | 300s | 900s | A count, not a headline |
| `GET /v1/sources/{slug}` | 300s | 900s | Publisher metadata barely changes |
| `GET /v1/issues/latest`, `GET /v1/issues` | 60s | 600s | A new edition shows within about a minute of publishing |
| `GET /v1/issues/{id}` | 600s | 3600s | A published issue never changes |
| `GET /v1/issues/{id}/pages/{n}` (unconsented) | 300s | 3600s | Frozen content; short enough that a takedown clears within minutes |
| `GET /v1/issues/{id}/pages/{n}` (consented) | not cached | — | It writes impressions whose ids the client reports clicks against |
| `GET /v1/feed`, `/v1/explore`, anything authenticated | not cached | — | Personal, and logs propensity at serve time; a cached ranking would log a decision no policy made |

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
