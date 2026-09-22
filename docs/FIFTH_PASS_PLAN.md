# Fifth pass — status analysis and plan

Written 2026-09-23, after running the site against **real data** for the first
time: a fresh local database, a real ingestion pass (664 articles from 21
sources across en/es/hi), and a real Aquila edition (9 pages). Every earlier
pass was reviewed against a hand-seeded corpus of ~29 demo articles. Real
content exposed problems the demo data was hiding. This document records what
was found and what to do about it, in order.

Method: every public route screenshotted at 1440×900 and 390×844, console
errors captured per page, the design detector run over `frontend/`, and the
relevant source read where a screenshot raised a question. Signed-in surfaces
(feed as a beta reader, saved, history, settings, onboarding) could not be
reviewed live — they need a real Supabase test account — and are assessed from
code only. That is the biggest gap in this analysis; see §5.

---

## 1. Where the product stands

**Built and working.** Three destinations (Home, Aquila, My Desk), search with
four filters and topic/source result groups, story pages, article pages, an
admin console covering nearly all of Stage 4 (sources health, ingest runs,
takedowns, taxonomy override, users and roles, per-user activity, invites,
feedback, flags, audit log, analytics with DAU/WAU/retention and CTR by
ranking policy), a Stage 5 heuristic ranker with an A/B split, a Stage 7
exploration deck, export and account deletion, consent, sitemap, RSS, JSON-LD,
a service worker, three locales. The e2e suite (axe on 8 routes, keyboard,
consent, auth redirect, structured data) is green.

**Not reaching anyone.** `main` holds only the initial commit; all 146 commits
live on `chore/scaffold`. The scheduled ingest and Aquila jobs cannot fire and
CI only runs on `main`/PRs. Until that merge happens, nothing in this document
is visible to a reader. This is a decision for you, not a UI task — it is
listed first because it gates everything else.

**Honest overall verdict.** The *design* is authored and specific — nobody
would mistake Aquila for a template. The *experience* is weaker than it looks,
because most of the features built around the product's differentiator (story
clustering) have nothing to show when real content arrives, and the empty
states they fall back to read as errors.

---

## 2. Findings from real data

Ordered by how much of the reader's experience each one damages.

### 2.1 Cluster-dependent surfaces are empty, or wrong — **P1**

After a real ingestion pass: **6 story clusters, every one single-source.**

- **Topic pages land on three empty boxes.** `/en/desk/medtop:11000000`
  (Politics) has 69 articles and 5 sources, but its default tab, Understand,
  shows "No major developments yet", "Not enough named-source coverage", "No
  story timeline yet". The reader's first impression of a topic with 69
  articles is that it has nothing.
- **Recurring programme titles become fake "stories".** The story page for
  "Tech Life" merges four unrelated BBC podcast episodes published across 21
  days ("AI can only communicate in languages…", "Scammers demand money from
  Instagram users…", "What should children learn…", "China is competing…").
  Same for "Tech Now", "BBC Inside Science", "Inside Health". This is a real
  bug independent of the embedder: identical programme titles collapse under
  title-based dedup, and the dedup window does not stop a cluster from
  absorbing an episode three weeks later.
- **Podcast and programme feeds pollute every top tier.** "Tech Life" sits in
  Home's hero tier, Aquila's right rail, and My Desk's worked example.
- **My Desk's worked example demonstrates nothing.** It picks the first topic
  with any story — which is "Climate", whose stories are a podcast title and a
  documentary, each "1 source · 1 language". The pitch above it promises
  "compare who is covering it"; the example shows one source. The same
  "Prison Letters" item appears three times on the one page.

*Partly a local artifact:* local dev uses the hashing embedder
(`EMBEDDER=hashing`); production ingest uses the real multilingual encoder
(`ingest.yml`), which will produce genuine multi-source, cross-lingual
clusters. But production cluster density has **never been measured** —
production ingest has never run (§1) — and the podcast-title bug happens with
either embedder. The UI must be designed for thin clusters, because early
production will have them too.

### 2.2 Aquila breaks with a real issue — **P1**

- **The masthead lists eight raw IPTC section names**, stacked ~220px tall on
  desktop and ~140px on mobile: "CONFLICT, WAR AND PEACE", "ARTS, CULTURE,
  ENTERTAINMENT AND MEDIA"… The fourth pass replaced the generic words with
  the issue's real sections (correct in principle), tested against a
  one-section demo issue. With nine pages it dominates the front page. A
  regression of my own making.
- **The contents sidebar is clipped at 1440×900** — the reference viewport —
  "Conflict, war a…", "Economy, bus…", "Science and te…" cut off at the
  window edge.
- **The lead's deck is cut off mid-sentence** by the fixed-height sheet
  ("Princess Diana's brother apologised to Morgan for a" — then nothing). A
  real three-line headline leaves no room for the deck the layout assumes.
- **Section names are raw IPTC labels** here and in "Related topics", while My
  Desk uses the curated consumer labels ("Culture", "Markets", "Climate"). Two
  vocabularies for the same thing.

### 2.3 Home — **P1**

- **"What matters" is just "newest".** For a signed-out reader the feed is
  chronological, so the hero is whatever landed last — today, a Piers Morgan
  celebrity spat. The label promises editorial importance the data does not
  back. Anonymous Home needs a real importance signal (source breadth of the
  cluster, source trust, recency blend) — all arithmetic on existing columns,
  no model (ADR 0004).
- **The Daily Brief duplicates the dense list.** The fourth-pass fix drew the
  Brief from feed positions 9–14; "More From The World" also starts at
  position 9. The first five rows under the tabs are the Brief, reprinted.
- **Hydration failure on every minute boundary.** `ArticleCard` formats
  relative time ("23 minutes ago") on the server and again on the client; when
  a minute ticks over in between, React discards the server HTML and
  re-renders the tree (captured in the console on `/en`). Visible as a flash,
  costs performance on exactly the route that matters most.
- **The two-column dense list reads ambiguously.** The left row's thumbnail
  sits flush against the right row's headline, so an image looks like it
  belongs to the story beside it.
- **Mobile Home is 9,400px** before "More headlines". On a phone the three
  tiers plus the rail stacked end to end is a long scroll with no summary.
- **Mobile shows the wordmark twice** ("JustNews" header, then "JUSTNEWS · A
  clearer tomorrow" directly below).

### 2.4 Search — **P1**

"trump" returns 40 results; the UN speech appears five times and the Burnham
meeting four times, from different outlets, as separate rows. Search is the
one surface where grouping by story is most useful and it does none. No query
highlighting, no suggestions while typing.

### 2.5 Article page is a dead end — **P2**

Title, picture, snippet, "Read the full story at BBC News" — then ~400px of
empty page. Nothing about the story it belongs to, the topic it is filed
under, other coverage, or what to read next. This is the page readers arrive on
from search engines and shared links; it currently gives them one exit, and it
leads off-site.

### 2.6 Empty states look like errors — **P2**

Neutral "nothing here yet" messages use `.notice` — a red left-border alert box
(detector: side-tab accent borders at `globals.css:1826` `.notice`,
`:2268` `.blindspot`, `:2487` `.callout`). A topic with no timeline is not an
error. The "Analysis" tab on every topic page is a "coming soon" stub — a
permanent dead end in primary navigation.

### 2.7 Smaller issues — **P3**

- The icon rail's "Sign in" label renders as a detached pill beside the 56px
  rail.
- The signed-out gate on My Desk says "This page shows things tied to your
  account" on a page full of public content.
- Login has no "Forgot password?" path.
- "Today at a glance: 6 stories" undersells a 664-article corpus; the stat
  counts clusters, which readers do not think in.
- The Brief says "Read today's issue" while the Aquila edition is labelled
  "Midday Edition" at 19:30 local — correct but confusing without a note on
  what editions are.

---

## 3. Features that would make it genuinely good

Grounded in what the product is for (PRODUCT.md: the cross-lingual reader) and
what it can honestly do (no article bodies, no model in the request path, no
invented numbers). Ordered by value.

| # | Feature | Why it matters | Builds on |
|---|---|---|---|
| F1 | **"The same story, in other languages"** on cards and story pages | The product's one structural differentiator is invisible today. A card that says "also reported in Español · हिन्दी" with a tap-through is the whole pitch in one line | `story_clusters.language_count`, story page's language groups; needs production's real embedder |
| F2 | **Follow a story** — "3 new reports since you last looked" | Turns a one-off read into a reason to come back, without push or email | `story_clusters.last_seen_at`, a new per-user `story_follows` row |
| F3 | **Publisher pages** `/[locale]/source/[slug]` | On the roadmap's own route list, not built. Every byline becomes a link; follow-source already exists with nowhere to land | `sources`, `FollowSourceButton` |
| F4 | **Useful article page** — the story it belongs to, other coverage, topic chips, follow, "next in this topic" | The landing page for search and social traffic | existing endpoints |
| F5 | **Search that groups by story**, highlights terms, suggests topics/sources while typing | Search is where duplicate coverage hurts most | `story_cluster_id` on results, `search_topics`/`search_sources` |
| F6 | **"New since your last visit"** marker on Home and My Desk | The simplest honest answer to "what changed" | a last-visit timestamp per reader (cookie for signed-out) |
| F7 | **"Why am I seeing this?"** wired to the real ranker | The component exists at `/dev/why` on mock data; design-system.md calls self-explaining cards non-negotiable | `services/ranking.py` factors |
| F8 | **Reader controls** — light/dark/system toggle, text size, keyboard shortcuts (`j`/`k`/`s`/`o`, `?` for help) | Power readers live in feeds; only Aquila has keys today | — |
| F9 | **How JustNews works** page — clustering, Perspectives, Aquila editions, privacy | Help & documentation scores 1/4; nothing explains the product's ideas | — |
| F10 | **Forgot password / magic link** | Basic account hygiene | Supabase Auth |

Deliberately *not* proposed: AI summaries or "why it matters" text (ADR 0004,
and no editorial voice), comments (roadmap decision), reader counts or other
numbers the data cannot back. Push notifications and email digests belong to
Stage 9 and wait for launch.

---

## 4. The plan

Correctness and data quality first — every feature in §3 sits on content that
is currently polluted — then the surfaces, then the new features.

**Prerequisite — deployment (your decision).** Merge `chore/scaffold` into
`main` so CI, the ingest cron and the Aquila cron actually run, then measure
production cluster density for a few days. Several decisions below (how often
multi-source stories exist, whether F1 has enough to show) depend on that
number.

### Chunk 1 — Content quality *(§2.1)*
Exclude audio/podcast/programme entries at ingest (feed-level flag plus
entry-level detection: enclosure types, known programme-title patterns); stop
clusters from absorbing entries outside the dedup window measured from the
cluster's *latest* article; a repair command to split the bad clusters already
stored.
**Accept:** no programme title forms a cluster; no cluster spans more than the
dedup window without new reporting inside it.

### Chunk 2 — Honest empty states *(§2.1, §2.6)*
Topic pages fall back gracefully: Understand shows the topic's latest
articles grouped by day when there are no multi-source stories, rather than
three empty boxes. My Desk's worked example picks the topic with the most
*sources*, not the first with any story, and never repeats an item on the page.
Empty states restyled as quiet typography, not red alerts. The Analysis stub
leaves the tab bar until it has content.
**Accept:** no route's default view is empty while it has articles to show.

### Chunk 3 — Aquila with real content *(§2.2)*
Masthead: the page count and the first three section names in curated labels,
"+ N more" — or the page count alone, whichever measures cleaner. Fix the
contents sidebar clip at 1440×900. Clamp the lead headline so the deck always
fits, and drop the deck rather than clip it when it cannot. Curated labels
everywhere a topic is named.
**Accept:** a nine-page issue renders at 1024/1440/1920 and 390 wide with
nothing clipped mid-word.

### Chunk 4 — Home that means it *(§2.3)*
An importance score for anonymous Home (cluster source breadth × source trust
× recency), so "What matters" is earned. Brief drawn from outside every
visible band. Relative times rendered client-only (or with
`suppressHydrationWarning` on the `<time>` element) to end the hydration
failure. Dense-list thumbnail alignment. One wordmark on mobile, and a
shorter mobile Home.
**Accept:** no hydration errors on `/en`; no article appears twice on Home.

### Chunk 5 — Article page and publisher pages *(F3, F4)*
Article page gains the story it belongs to, other coverage, topic chips with
follow, and next-in-topic. New publisher route with its latest coverage,
follow button and role (ADR 0013). Bylines link to it everywhere.

### Chunk 6 — Search that groups *(§2.4, F5)*
Results grouped by story ("5 outlets · 1 language" with the best-ranked
headline leading), query highlighting, typeahead for topics and sources.

### Chunk 7 — The differentiator, visible *(F1, F2, F6)*
"Also in Español · हिन्दी" on cards and story pages. Follow a story, with a
"new reports since you looked" line. "New since your last visit" on Home and
My Desk.

### Chunk 8 — Reader controls and help *(F7, F8, F9, F10)*
Theme toggle, text size, feed keyboard shortcuts with a `?` overlay, the
how-it-works page, forgot password, and "Why am I seeing this?" wired to the
real ranker's factors.

### Chunk 9 — Signed-in review and QA
Create a test account, review feed/saved/history/settings/onboarding live the
way this pass reviewed the public routes, fix what it finds, re-run the full
e2e suite (including the three signed-in specs currently skipped) and measure
performance against the second-pass baseline.

---

## 5. What this analysis could not see

- **Signed-in surfaces.** No test account was available; the personalised feed,
  saved, history, settings, onboarding and the exploration deck were assessed
  from code only. Chunk 9 closes this.
- **Production cluster density.** Local clustering uses the hashing embedder.
  Real density is unknown until production ingest runs (§4 prerequisite).
- **RTL.** Still unexercised — no RTL locale ships.

---

## 6. Heuristic scores (Nielsen, 0–4)

| # | Heuristic | Score | Main reason |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Skeletons, degraded banners and pending states exist; no "last updated" on Home |
| 2 | Match with the real world | 2 | "What matters" on a recency sort; raw IPTC labels; podcast titles presented as stories |
| 3 | User control and freedom | 3 | Undo on not-interested, URL-backed tabs, Esc in Aquila |
| 4 | Consistency and standards | 2 | Curated vs raw topic labels; neutral empty states styled as alerts |
| 5 | Error prevention | 3 | Assessed mostly from code |
| 6 | Recognition rather than recall | 2 | Icon-only rail on desktop; no suggestions in search |
| 7 | Flexibility and efficiency | 2 | Keyboard shortcuts in Aquila only; no theme toggle |
| 8 | Aesthetic and minimalist design | 3 | Strong identity, undermined by repeats (Brief, My Desk) and empty boxes |
| 9 | Error recovery | 3 | Degraded states offer a way forward |
| 10 | Help and documentation | 1 | Nothing explains clustering, Perspectives or editions |
| | **Total** | **24/40** | **Acceptable** — the foundation is good; real data exposed the gaps |
