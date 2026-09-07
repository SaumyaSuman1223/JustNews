# Third-pass plan

Response to `JUSTNEWS_THIRD_PASS_DESIGN_AUDIT.md`, in the shape §45 asks for
(sections A–K), after the repository and live-deployment inspection §44
requires.

---

## 0. Deployment truth — most of this audit is already live

§44 step 2 and §43's Phase 0 both say to verify the deployed code before
planning. Doing that first changes the scope of this brief substantially.

Measured on `just-news-pi.vercel.app` just now, at 1440 and 1920:

| Audit asks for | Live right now |
|---|---|
| §6 AQUILA TRIBUNE + THE WORLD IN CONTEXT | Both present; title **86px** at a 1175px paper — inside §6's 78–100px band |
| §7 no permanent category navigation | None present |
| §9/§10 right-edge sliding utility bar, separate from the editorial rail | Both present and separate |
| §12 halftone on every Aquila image | Present |
| §13–15 three-level Home hierarchy | "What matters / What you should know / More from the world" |
| §14 The Big Three (1 dominant + 2) | Present |
| §17/§18 concise summaries, no live-blog leakage | Shipped, and the production corpus was repaired today |
| §19 statistics as quiet metadata | Rule and small caps, no card |
| §23/§25/§26 My Desk header, What Changed, Understand | All present |
| §28 slim icon rail, 52–60px | **56px** |
| §29 Aquila does not use the icon rail | Correct |
| §31 quiet footer | Identity + one line |
| §8 left rail: motto, attribution, IN FOCUS, headline, source | All present |
| §8 TODAY'S HIGHLIGHTS, numbered | Present |
| §27 search results heading and count | "138 results" |

The second-pass programme (eight chunks) merged to `main` earlier today and is
deployed. The auditor was looking at a site that had most of it — so a large
part of this document restates work that already exists.

**This is not a complaint about the audit.** It matters because §53 says "do
not continue making tiny cosmetic adjustments" and asks for experience-level
recomposition. If I treated this brief as a fresh to-do list I would spend the
whole pass rebuilding things that already pass their own acceptance criteria,
and never reach the parts that are genuinely missing. The gap list below is
what I could not find on the live site.

**One likely cause of the low ratings.** My Desk is scored 3.5/10. Measured
signed out — which is how an auditor without an account would see it — the
page is dominated by the sign-in gate: `tiles: 0`, and the first thing in the
text is "Sign in to see this". The workspace *is* there, behind auth. Some of
what §23 calls "too thin" is a signed-out impression of a page whose content
is gated, not an absent page. That changes the fix: the signed-out desk needs
to carry more of its own weight, which is cheaper and more valuable than
rebuilding the signed-in workspace that already exists.

---

## A. Current-state architecture

| Layer | State |
|---|---|
| Routing | `(app)` shell + `(reader)` group; URLs unchanged |
| App shell | 56px icon rail, tooltip labels that are also the accessible names, quiet footer |
| Aquila shell | Dark `#20211f` workspace, `ReaderUtility` right-edge panel, no global nav |
| Aquila page | `IssuePaper` — masthead, rule, `paper__focus` / `paper__lead` / `paper__highlights` |
| Aquila images | `HalftoneImage` — SVG `feColorMatrix` + dot screen, client-side, no server pipeline |
| Home | `home__hero` (lead + 2), `home__know` (2 picture + 4 text), `home__feed` (2-col dense), rail |
| My Desk | `WhatChanged` + `DeskTiles` + `AddTopicPicker`; topic page = `Understand` (3 modules) / Latest / Analysis |
| Search | Query + topic + language filters, recent searches, results heading, real total |
| Cards | Four variants: `lead`, `secondary`, `list`, `compact` |
| Content | Cleaned at ingestion (`make_snippet`): entities, live-blog furniture, 200-char summary |
| Editions | `issues` + `edition_slot` (06:00/14:00/22:00 UTC), composed by the ingestion CLI |

## B. Audit findings — measured gaps only

Each of these I confirmed absent or out of spec on the live site.

**Aquila (§5, §8, §11, §46)**

1. **Column proportions are off.** Measured 14% / 53% / 21% against §8's
   15–17% / 58–62% / 23–27%. The lead is the one that matters — it is 5
   points under the floor.
2. **No lower row.** §8 asks for ~3 major stories under the three columns.
   The paper has exactly three children: focus, lead, highlights.
3. **No page references.** Zero matches for `PAGE \d+`; no "CONTINUED ON
   PAGE X". §8 and §46 both ask for them.
4. **The paper does not scale on large desktop.** 1175×783 at 1440 *and* at
   1920 — identical. On a 1920 screen the newspaper should be the dominant
   object and instead it leaves ~700px of empty workspace.
5. **94px of scroll at 1440×900.** §5 wants the paper to fit the viewport.
6. **No swipe, no drag.** `IssueReader` has keyboard and buttons; grep finds
   no touch, pointer or drag handling. §11 asks for both.
7. **Mobile paper is 298px wide** on a 393px screen — a lot of margin for a
   surface that is meant to dominate.

**Home (§16, §20, §21, §22)**

8. **Two story types missing.** Have `lead`/`secondary`/`list`/`compact`
   (≈ Lead/Standard/Standard/Brief). §16's **Feature** and **Cluster** do not
   exist.
9. **The Daily Brief is a bordered card with a bulleted list.** §20 wants
   numbered lines (`01 What changed overnight`); §33 wants it to stop being a
   card.
10. **Source diversity is invisible.** Cards show `SOURCE · TIME`. §21 wants
    "7 sources · 4 countries · 2 languages" on a significant story. The data
    exists — `story_clusters` carries `source_count`, `language_count`,
    `article_count` — but `ArticleOut` does not expose it.
11. **No cluster surface.** §22's "THE STORY — 7 sources are covering this"
    does not exist anywhere.

**My Desk (§24)**

12. **Topic selection is the raw IPTC taxonomy.** Live chips read "Arts,
    culture, entertainment and media", "Disaster, accident and emergency
    incident". §24 is explicit: users should think "I care about AI", not
    "I must choose an IPTC taxonomy". This is the single clearest confirmed
    gap in the document.

**Search (§27)**, **Moments (§34/§35)**

13. Search has no editorial framing ("What are you trying to understand?") and
    no source or date filter.
14. No story expansion, no topic unfolding — §35's signature gestures for
    Home and My Desk. Aquila's page turn exists and is the one that works.

**Conflicts I will not silently resolve**

- **§8's "2–3 short context paragraphs" and CONTINUED ON PAGE X.** Third time
  this has been asked for. The product stores no body text and
  `CLAUDE.md` forbids it. Page references I *can* do honestly, because pages
  are real. Context paragraphs I cannot, and will not fake with the snippet
  repeated. Unchanged from both previous passes.
- **§21's "4 countries".** `sources.country` exists, so this is real and
  computable. "3 perspectives" is only honest where `source_role` is
  populated; where it is not, the line must omit it rather than guess.
- **§24 curated topics vs IPTC.** `CLAUDE.md` requires IPTC concept IDs as the
  canonical key. A curated layer is a *presentation* mapping onto those IDs —
  never a second taxonomy in the database. That is the only version of §24 I
  will build.

## C. Component strategy

**Reuse unchanged:** `ReaderUtility`, `HalftoneImage`, `Timeline`,
`Perspectives`, `Understand`, `WhatChanged`, `PrimaryNav`, `SearchControls`.

**Refactor:** `ArticleCard` gains `feature` and `cluster` variants (the
variant set is already the right abstraction — it grows, it is not replaced).
`IssuePaper` gains a lower row and page references. `DailyBrief` loses its
card and gains numbering. `IssueReader` gains pointer/touch page turning.

**Replace:** `AddTopicPicker`'s flat taxonomy list becomes a curated topic
chooser over the same IPTC ids.

**Build:** `StoryCluster` presentation component (§22), `SourceDiversity`
line (§21), curated topic map.

## D. Route strategy

No route changes. Every URL stays. §22's cluster view has a home already:
`/[locale]/story/[id]` exists and is the coverage view — it gets the §22
composition rather than a new route.

## E. Data strategy

Backend stays still except for one measured need (§42 permits exactly this).

- **Change:** expose cluster counts alongside an article, so §21 and §22 can
  render without N+1 lookups. Preferred shape: add `story` (source_count,
  language_count, country_count) to `ArticleOut`, populated by a join that
  already has the cluster in scope. One migration is *not* required — the
  columns exist; this is a serialization change plus a query join.
- **Unchanged:** feed, ranking, follows, saves, history, search, issues,
  perspectives, interactions, admin, auth, ingestion, retention.
- **Propensity logging is untouched.** Every new surface that shows a ranked
  item keeps logging through `services/interactions.py`.

## F. Image strategy

Unchanged and already correct: halftone is client-side SVG + CSS over the
hotlinked publisher image, with the original as graceful fallback. §12's
explicit instruction not to build server-side asset processing is already
honoured. The only work is tuning dot scale to §12's 2–4px / 1.5–3px bands
and confirming the palette stays inside cream/ink/muted red.

## G. Edition strategy

Unchanged. `edition_published_at` derives the timestamp from the slot, the
composer runs on schedule, `repair-edition-times` exists for drift, and the
three editions are selectable in the utility panel. Nothing in this audit
requires touching it.

## H. Interaction strategy

- **Icon rail** — done; keyboard path and accessible names already asserted in
  `e2e/keyboard-nav.spec.ts`.
- **Utility bar** — done; overlay, no reflow, Escape returns focus.
- **Page turn** — buttons and keyboard done; add pointer drag and touch swipe,
  both with the same 350–550ms transition and both respecting reduced motion.
- **Story expansion (§35)** — headline to context without a navigation, on
  Home's lead only. One gesture, one surface, not a site-wide behaviour.
- **Topic unfolding (§35)** — My Desk topic opens its Understand modules in
  place rather than as a page load.

## I. Responsive strategy

Desktop keeps the editorial grids. Tablet reduces column count and keeps
hierarchy. Mobile is single-column with the bottom tab bar, except Aquila,
which keeps the paper and gains swipe. The measured mobile Aquila paper
(298px of 393px) gets more of its viewport. No horizontal scroll at any width
— currently true and asserted by the QA matrix.

## J. Testing strategy

The matrix that already runs each chunk: 9 routes × 5 widths × 2 themes for
overflow, axe at 390 and 1440 in both themes, keyboard tab-stop naming,
reduced-motion settled state, `pytest`/`mypy`/`ruff check` + `format`,
`pnpm typecheck`/`lint`/`build`, `make generate-client` whenever the API
surface moves. Plus, for this pass: the §9-phase edge cases the audit names —
long headlines, missing images, missing metadata, multilingual text, edition
boundaries.

## K. Deployment strategy

`main` is now the deployed branch and the ingestion cron runs from it —
verified today, with new articles arriving clean. Each chunk lands on a branch,
gets the full gate, and is verified against the **live** site after deploy, not
only locally. That check is what caught this audit's premise and what caught
the empty-focus-column defect last pass.

---

## The chunks

Ordered by measured gap size, not by the audit's §43 phase list — that list
assumes Phases 1, 4, 5, 6 and 7 are unbuilt, and they are largely built.

### Chunk 1 — Aquila front page composition *(§8, §46)*
Fix the three column proportions to spec. Add the lower row of ~3 major
stories. Add real page references — `PAGE 4` in the rail, and continuation
references only where the story genuinely continues on a page the issue has.
Composer change: the front page needs a fourth role band, so `FRONT_PAGE_*`
counts and the role vocabulary move together.
**Accept:** measured 15–17 / 58–62 / 23–27; a lower row present; every page
reference resolves to a page that exists.

**Shipped, with two corrections found by measuring rather than assuming.**

*Column proportions were never actually broken.* §0's 14/53/21 figure was
measured against the sheet's own padding, not the grid's content box. Against
the right denominator: 15.5 / 58.2 / 23.3 — already inside every band. No CSS
changed here; the composer's `grid-template-columns: 16fr 60fr 24fr` from the
second pass was correct all along.

*Page references are a real cross-reference, not a fabricated continuation.*
`SlotOut` gained `page_ref: int | None` — the section page a front-page
story's own primary topic occupies in the same issue, computed at read time
from two small bulk queries (`primary_topics_for_articles`,
`section_page_numbers`), no schema change. Deliberately not "this story
continues on page X" — the product stores no body text, so nothing
continues anywhere; what's real is that the topic has fuller coverage a page
away, the way a broadsheet's front page points a reader inside. Clickable
where a reading session exists (`onGoTo` turns the page without a
navigation), inert text otherwise. Three integration tests: a topic with a
section gets its reference, a topic without one gets none, and a section
page's own slots never carry a reference back out.

*The lower row exists, but not as first planned.* The composer's
`FRONT_PAGE_SECONDARIES` went from 3 to 6 — one count, split by position in
the frontend (first 3 to the right rail, rest to a new row), not two composer
roles. The first attempt also moved TODAY'S HIGHLIGHTS out of the left rail
to sit under the new row, per §8's literal layout. Measured: the lead alone
is 531px of a ~587px body budget at 1440×900, and the sheet clips rather than
scrolls (`overflow: hidden`, deliberate, from the second pass) — moving
highlights added ~150px of content the page did not have. Reverted that one
piece: highlights stays in the left rail, where it already fit, and gained
page references there instead. The lower row itself is three single-line,
byline-less headlines — the plainest thing on the page, sized to whatever
the lead's own height leaves over. Also trimmed to make room: the lead's
deck from 3 lines to 2, the right rail's headlines from 3 lines to 2 (it had
become taller than the lead), and two small paddings.

Measured after: 8px of residual overflow at 1440×900 (rounding-level; the
footer renders fully) versus 144px on the first attempt. At 768px height the
page still clips — but production already clipped 27px there before this
chunk touched anything, and this chunk added 22px more to an already
pre-existing gap. That gap is Chunk 2's stated scope (scale the paper with
the viewport), not something to paper over here by cutting content further.
Full QA matrix (5 widths × 2 themes, axe at the extremes) clean on both the
front page and a section page.

### Chunk 2 — Aquila as the dominant object *(§5, §11, §40)*
Scale the paper with the viewport so 1920 gets 1300–1450px. Remove the 94px
of scroll at 1440×900. Add pointer drag and touch swipe to page turning, both
reduced-motion aware. Give the mobile paper more of its screen.
**Accept:** paper grows at 1920; no scroll at 1440×900; swipe turns a page on
a real touch device profile; drag has a keyboard equivalent already.

### Chunk 3 — Source diversity, made visible *(§21, §16 Cluster)*
The one backend change: cluster counts on `ArticleOut`. Then the `cluster`
card variant, and the diversity line on significant stories — sources,
countries, languages, each omitted when unknown rather than guessed.
**Accept:** every number traces to a column; a single-source story shows no
diversity line at all; `make generate-client` committed.

### Chunk 4 — The story as a first-class object *(§22)*
`/story/[id]` becomes §22's composition: the story, who is covering it, what
differs. Built from clusters and `source_role`, which both exist.
**Accept:** nothing on the page is inferred; every source is a real link.

### Chunk 5 — My Desk topic selection *(§24)*
A curated topic layer — AI, Markets, India, Space, Climate, Energy,
Semiconductors, Politics — mapping onto IPTC concept ids, which stay the
canonical key. Editorial chips, not SaaS tags. Plus the signed-out desk
carrying real content rather than a gate.
**Accept:** no raw taxonomy label on screen; every curated topic resolves to
real IPTC ids; signed out shows something worth reading.

### Chunk 6 — Feature stories, the Brief, and Search *(§16, §20, §27)*
The `feature` card variant. The Brief renumbered and de-carded. Search gains
its editorial framing and a source filter.
**Accept:** Home uses at least four distinct story compositions; the Brief is
not a card; search filters still return exactly what the count claims.

### Chunk 7 — Moments *(§34, §35)*
Story expansion on Home's lead; topic unfolding on My Desk. Two gestures,
built from composition, no new animation library, both reduced-motion aware.
**Accept:** each gesture works by keyboard; neither is required to reach any
content.

### Chunk 8 — QA and the audit's edge cases *(§43 Phase 9, §51)*
The full matrix plus long headlines, missing images, missing metadata,
multilingual text, edition boundaries. Performance re-measured against the
numbers recorded in the second-pass plan, so any regression is visible.

---

## Risks

| Risk | Handling |
|---|---|
| Rebuilding what already ships | §0's measured table is the guard; every chunk states what it found live before changing it |
| The one backend change grows | It is a join and a serializer field; if it needs a migration, that is a signal to stop and re-plan |
| Curated topics become a second taxonomy | The map is presentation-layer and IPTC ids stay canonical (`CLAUDE.md`) |
| "Moments" become decoration | §36 bans the usual additions; two gestures only, both keyboard-reachable |
| Page references that lie | A reference renders only when the target page exists in the issue |
