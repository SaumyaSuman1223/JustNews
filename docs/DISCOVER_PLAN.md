# Discover: plan

Status: proposed, 2026-09-23. It replaces Home and My Desk with a single
Discover surface, modelled on Perplexity Discover. It also fixes production
latency. It supersedes the IA in ADR 0011 (Home / Aquila / My Desk).

## 1. What the reader gets

**Left sidebar** (collapsible, and extensible: items come from one config array)
- Search: a real input with type-ahead, not a link to a page.
- Discover (the feed), Aquila, Saved, History.
- Account at the bottom: avatar, name, settings, sign in/out, display, language.
- New items are one entry in `lib/nav.ts`, not a layout change.

**Top bar of Discover**
- `For You` · `Top` · `Topics ▾`
  - The Topics dropdown lists the curated topics, and selecting one swaps the
    feed in place.
- On the right: a customise button (rail widgets) and Share.

**Feed**, in the Perplexity rhythm:
1. A lead story: headline, "Published 3 hours ago", snippet, image on the
   right, then a sources row, save and more.
2. A row of three cards (image, headline, sources row).
3. A wide feature (image left, text right).
4. Repeat.

Other feed behaviour:
- **Sources row.** Up to three publisher favicons plus "26 sources", showing
  the story cluster's real outlet count. It opens the story page, which lists
  every outlet. We show original sources only: no AI summary (per your
  instruction, and ADR 0004).
- **Infinite scroll** with cursor pagination. The next page is prefetched
  before the reader reaches the end.
- **For You.** Signed-in readers get the personal ranker (with impressions and
  propensity logged as now). Signed-out readers with interests get the
  importance order filtered to those topics. Anyone with neither gets Top plus
  the "Make it yours" card.
- **Top.** `/v1/articles/top`: recency × breadth of coverage × trust, one row
  per story.
- **Topic.** That topic's feed, in the same layout.

**Right rail**
1. **Make it yours**, for new readers only.
   - Topic chips and Save interests. It can be dismissed.
   - Signed out, the choice lives in a cookie. Signed in, it becomes topic
     follows, and anything chosen before sign-in carries over.
2. **Widgets**, from a registry (`components/rail/registry.ts`). Each widget is
   `{id, title, component, defaultOn}`. The reader can reorder or hide them from
   the customise button, and the order is stored per reader. Adding a widget
   later is one file plus one registry line.
   - **Weather:** now, plus 5 days, for the reader's chosen city.
   - **Market Outlook:** four tiles with sparklines.
   - **Trending Companies:** see the decisions in §4.

My Desk is removed. Its useful parts (topic pages, following) move into
Topics, For You and Make it yours. `/desk` redirects to `/?tab=for-you`.

## 2. Why production feels slow (measured today)

| Path | Time |
|---|---|
| `just-news-pi.vercel.app/en` | 0.6–2.1s TTFB |
| `/en/aquila` | 2.5–3.9s TTFB |
| API `/health` | 0.4s |
| API DB-backed reads | 1.5–1.8s each |
| Same pages on a local production build | 10–60ms warm |

The code is fast; the deployment topology and the missing caches are not:

1. **Regions do not match.**
   - Vercel functions run in `iad1` (US East).
   - The API runs in Render `oregon`.
   - Supabase's region is unknown to me (see §4). Health takes 0.4s but any
     DB read takes 1.5s+, so the database is almost certainly far from the
     API. Every query pays that distance, several times per request.
2. **Upstash rate limiting runs on every API request, with a new HTTPS client
   each time.** `core/ratelimit.py` opens an `httpx.AsyncClient` per call, so
   every request pays a fresh TCP and TLS handshake to Upstash before any work
   starts.
3. **Nothing is cached anywhere.**
   - Every page is `private, no-store`.
   - Next's client router cache for dynamic pages is 0s, so tab switches and
     back/forward refetch everything.
   - The API has no read cache.
4. **Waterfalls.** The app layout awaits `getSession()` and then `getMe()`
   before rendering anything, on every navigation. Pages then add their own
   serial fetches.
5. **Cold starts.**
   - Render free spins down after 15 minutes idle.
   - The uptime ping runs every 15 minutes, and GitHub cron routinely runs
     late, so readers still hit 30–50s wake-ups.
6. **Motion.**
   - A link click shows nothing until the server answers.
   - Skeletons don't match every layout.
   - Tab changes are full navigations.

## 3. The work, in order

Each part ships green on its own.

**Part A: latency** (biggest win, smallest diff)
- Co-locate Vercel functions, the Render API, Supabase and Upstash in one
  region (`vercel.json` `regions`, `render.yaml` `region`).
- Rate limiter:
  - one long-lived `httpx.AsyncClient` with keep-alive
  - an in-process first pass
  - Upstash only for the shared count
- A **Redis read-through cache** for anonymous hot reads, in a new
  `core/cache.py`. It uses Upstash, which CLAUDE.md already allows for hot keys.
  - Endpoints and TTLs:
    - `articles/top`: 60s
    - first page of `articles` per language/topic: 60s
    - `trending`: 60s
    - `stats`: 5 min
    - `issues/latest` and issue pages: 10 min (issues are immutable)
    - `sources/{slug}`: 10 min
    - widget data: see Part E
  - Stale-while-revalidate, a stampede lock, and keys versioned by schema.
  - Personal feeds are never cached: they log propensity at serve time, and a
    cached ranking would log a decision nobody made.
  - When Redis is down, reads fall back to the database. They never fail.
- Next:
  - `staleTimes.dynamic: 30` so back and tab switches are instant
  - `getMe` deduped with `cache()`
  - the layout fetches in parallel
  - `Cache-Control: s-maxage` + SWR on anonymous route handlers
- A keep-warm ping every 10 minutes (Render free allows one always-on
  service: 750h/month).
- The ADR records the cache policy per endpoint, per CLAUDE.md's definition
  of done.

**Part B: shell**
- The new left sidebar (collapsible; a drawer on mobile).
- The top tab bar.
- Nav config in one file.
- Shared layout, so switching between For You, Top and Topics keeps the shell
  mounted.
- Instant skeletons, the View Transitions API for tab changes, and
  reduced-motion respected.

**Part C: Discover feed**
- The lead / three-card / wide-feature rhythm.
- The sources row. The API adds `cluster_sources: [{slug, name, favicon}]` (top
  3) to article responses.
- Infinite scroll with TanStack Query (already in the stack) and prefetch of
  the next cursor page.
- For You / Top / Topic data wiring.
- Remove Home's tiers and My Desk, with redirects.

**Part D: Make it yours + widget rail** (built, 2026-09-23. Rail order and
visibility are a cookie for every reader for now, not a `user_preferences`
column: the cookie already renders server-side with no flash, and a synced
per-account preference is a later migration once readers ask for it on a
second device.)
- Interest chips and the cookie → follows bridge.
- The widget registry and the customise panel.
- Order and visibility stored in a cookie when signed out; signed in, a new
  `user_preferences` JSONB column (migration 0019, with RLS).

**Part E: widgets and their data**
- **Weather:** Open-Meteo (free, no key).
  - City search via Open-Meteo geocoding.
  - Redis-cached per rounded coordinate for 30 minutes.
- **Market Outlook:** the provider decision is in §4.
  - A scheduled job (GitHub Actions, every 15 minutes during market hours)
    writes snapshots to the database, and the API serves them from cache.
  - No market API is called in a request path, and free-tier quotas can't be
    exhausted by traffic.
- **Trending Companies:** see §4.
- Every external call has an explicit timeout and retry, per CLAUDE.md.

**Part F: QA**
- Measure production TTFB and navigation times before and after.
- Axe and keyboard specs on the new shell.
- Mobile, RTL and both themes.

## 4. Decisions (answered 2026-09-23)

1. **Supabase is in Tokyo (ap-northeast-1).**
   - Render has no Tokyo region; Singapore is the nearest (~70ms to Tokyo,
     against ~100ms from Oregon).
   - Target: Render `singapore`, Vercel functions `hnd1`, Upstash
     `ap-northeast-1`.
   - The Redis cache is what keeps most reads off the Singapore→Tokyo hop
     entirely.
   - Render cannot move an existing service between regions. The Blueprint
     change creates a new service, and the env vars and the Vercel
     `API_URL` must be pointed at it.
2. **Market data:** Finnhub (free key, `FINNHUB_API_KEY`) for ETF proxies,
   labelled as such, plus CoinGecko for Bitcoin. A scheduled job writes
   snapshots; no market API is called in a request path.
3. **Trending Companies:** the companies most mentioned in today's
   headlines, from a curated list with tickers, each with its quote.
4. **Weather:** the reader picks a city (Open-Meteo geocoding), stored in a
   cookie, with an optional browser "use my location". No IP geolocation.
