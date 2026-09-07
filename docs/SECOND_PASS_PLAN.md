# Second-pass plan

Response to `JUSTNEWS_SECOND_PASS_LIVE_SITE_AUDIT.md`. §43 asks for inspection
before editing and §44 for a plan before major changes; both were done against
the **live deployment**, not the local build, because §2 makes deployment the
first question.

---

## 0. Deployment truth (§2) — the audit's premise is half wrong, and the half
that is right matters more than the audit realises

**The frontend IS deployed and current.** Measured on
`just-news-pi.vercel.app` just now:

| Audit claim about live site | Actual |
|---|---|
| "The Aquila Tribune" | **AQUILA TRIBUNE** ✓ |
| No strap | **THE WORLD IN CONTEXT** ✓ |
| Old app shell | Reader shell, no `.shell` ✓ |
| No halftone | `#aquila-halftone` present, applied ✓ |
| Old 9-page web structure | 6-page issue, reader ✓ |

So Chunks A–H did reach production. The auditor was looking at a cached or
pre-deploy page for those four points.

**But the data is stale, and that is a real bug.** Production issue 7:

```
published_at: 2026-09-06T10:50:02.118400Z    slot: morning
roles on page 1: lead 1, secondary 3, brief 7   ← no `focus`
```

10:50 is not 06:00, and the sub-second precision (`.118400`) is a wall-clock
stamp. The composer that wrote this issue **was running pre-Chunk-A code**.
The missing `focus` role says the same thing.

The likely cause: scheduled GitHub Actions run from the **default branch**,
and `origin/main` was `Initial commit` at last fetch while all this work sits
on `chore/scaffold`. I cannot confirm from this sandbox — no network git.
**This is question one for the user** (§0 below).

**A defect this exposed.** The front page reserves a left rail for the `focus`
slot. An issue composed without one renders that column *empty* — visible on
production right now. My local data always had a focus slot, so I never saw
it. Same class as the empty-state contrast bug CI caught in Chunk B: a state I
could not reach locally.

---

## 1. Current architecture (§44)

| Layer | State |
|---|---|
| Routing | `(app)` shell group + `(reader)` group; route groups, URLs unchanged |
| App chrome | `.masthead` sidebar, **320px**, labelled links |
| Aquila shell | `.reader` dark ground, left edge-nav (`AquilaSidebar`), `<main>` |
| Aquila page | `IssuePaper` — masthead, rule, focus/lead/brief/highlights grid |
| Aquila utility | `.aquila__rail` — editions + pages, **permanently visible, 280px, right** |
| Images | Hotlinked, `HalftoneImage` + SVG filter + CSS dot screen |
| Editions | `Issue.published_on` + `edition_slot` + derived `published_at` |
| Content | `snippet` capped at 300 chars, rendered raw |

## 2. Current problems — measured, not assumed

**Structural, and the reason Aquila still reads as a webpage:**

| §35 target (1440×900) | Live | |
|---|---|---|
| paper width 1080–1180 | **1004** | narrow |
| paper height 700–790 | **1181** | **50% too tall** |
| ratio 1.45–1.55 | **0.85** | **portrait, should be landscape** |

At 1920: spec 1300–1450 × 820–900; live **1100 × 1262**, ratio 0.87.

This is the finding. The paper is a **portrait page that scrolls**, so turning
pages is decorative — the reader scrolls instead. A newspaper page is
landscape and fits. Fixing the geometry is what converts "webpage with
newspaper styling" into "newspaper", and no amount of type or colour work
substitutes for it.

**Also confirmed live:**

1. `.aquila__rail` (280px) is permanently visible — §12/§13 require the
   utility sidebar to be edge-triggered and overlaying, and the *editorial*
   right rail to live inside the paper. We have the opposite: utility outside
   but always-on, no editorial right rail inside.
2. The app sidebar is **320px with labels**; §14 wants a **52–60px icon rail**.
3. Snippets run to the full 300-char cap. Live examples: *"Premier League
   buildup to Arsenal v Chelsea, plus Everton v Manchester United and WSL —
   matchday live"* (§21's live-blog leakage, verbatim).
4. **HTML entities are not decoded**: `Antonelli&#039;s` renders literally on
   Home right now. Not in the audit; found while measuring.
5. "Today at a glance" is a bordered dashboard card (§22 wants quiet metadata).
6. Empty focus column, per §0.

**Already satisfied — no work needed:** masthead identity and size (78px at
1440, 86px at 1920, both in §36's band), halftone on every image, Cormorant
only, no Samarkan, keyboard set incl. Home/End, reduced motion, page-turn
450ms, three tiers on Home, axe clean in both themes at five widths.

## 3. Conflicts to settle, not silently resolve

- **§9 vs §7.** §9 says remove `News · Ideas · People · Perspectives`; §7's
  header keeps `NEWS PEOPLE IDEAS PERSPECTIVE` in the right column. Reading:
  §9 bans them as *navigation*, §7 keeps them as *masthead furniture*. Ours is
  non-clickable standing type, so it already satisfies both. **No change.**
- **§11 "2–3 short context paragraphs" and "CONTINUED ON PAGE 2"** — repeated
  from the first brief. Still impossible: the product stores no body text.
  Unchanged adaptation: snippet as deck, page refs only where real.
- **§7's left column** wants `A CLEARER TOMORROW` — that is JustNews's line,
  not the Tribune's. Using it inside the paper blurs the two identities the
  product is trying to separate. Flagging; I would keep the edition/volume
  there and put the JustNews line in the left rail's quote slot per §11.

---

## 4. The chunks

Ordered so structure precedes decoration, and so the thing most responsible
for "generic webpage" is fixed first. §42's phase list assumes the reader and
editorial grid do not exist; they do, so these differ.

### Chunk 1 — Deployment truth and edition data *(small, blocking)*
Confirm what runs the composer; get `main` and the workflow onto post-Chunk-A
code; run `justnews-ingest repair-edition-times` against production; make the
front page degrade correctly when an issue has no `focus` slot (collapse the
column, do not reserve it).
**Accept:** production morning edition prints 06:00; no empty column; a
newly composed issue carries a focus slot.

### Chunk 2 — Aquila paper geometry *(the big one)*
Landscape sheet that fits the viewport: §35's widths, heights and 1.45–1.55
ratio at 1440 and 1920. This means the front page composes into a page that
*ends*, with overflow becoming page 2 rather than scroll. Reworks column
balance, lead image scale, and how many slots a page holds — likely a
composer change (slots per page) as well as CSS.
**Accept:** measured ratio in band at both sizes; no vertical scroll inside a
page at 1440×900; page-turn becomes the way to read on.

### Chunk 3 — Aquila utility bar and editorial right rail *(§12, §13)* — **mostly shipped inside Chunk 2**
The sliding utility panel (`ReaderUtility`) and the editorial left rail landed
with the geometry work, because a landscape page that fits could not be
measured while a 280px utility column was still taking the width. What is
left of this chunk is the *right* editorial rail inside the paper
(Technology / Economy / Climate), which now belongs with Aquila's remaining
composition work rather than on its own.


Move `.aquila__rail` out of the layout and into a right-edge sliding panel:
20–28px trigger, 280–320px panel, 200–280ms in / 250–400ms out, overlays
without reflowing the paper, keyboard-reachable with Escape (§39). Then build
the *editorial* right rail inside the paper — Technology / Economy / Climate
with varied composition (§11).
**Accept:** nothing permanent on the right; paper does not reflow when the
panel opens; full keyboard path; axe clean.

### Chunk 4 — Icon rail for Home and My Desk *(§14, §29, §30)*
Replace the 320px labelled sidebar with a 52–60px icon rail: tooltips, active
state, visible focus, accessible names that do not depend on the tooltip
(§39). Quieten the footer to one line (§30).
**Accept:** rail measures 52–60px; every item reachable and named by keyboard;
mobile does not lose screen to navigation (§38).

**Shipped.** Measured 56px at 900, 1440 and 1920; tab bar unchanged below
900. The label is the link's accessible name *and* the tooltip, hidden with
`opacity` rather than `display`/`visibility` so it never leaves the
accessibility tree — asserted in `e2e/keyboard-nav.spec.ts`. Search field and
language control left the rail: search is a destination in it, and the
language control moved to the footer, which §30 rebuilt as one quiet line
(identity + `Privacy · Send feedback · languages`). Axe clean in both themes
at 390/900/1440; no horizontal overflow at 390/768/900/1440/1920; tooltip
flies out to the correct side under `dir="rtl"`.

### Chunk 5 — Home composition *(§15–§19, §31, §32)*
The Big Three (one dominant + two), then a varied grid for What You Should
Know, then More From The World. Break the repeated card rhythm: alternate
image-left/right, text-dominant entries, varied headline weight.
**Accept:** no two adjacent sections use the same composition; first story
dominates unmistakably; three tiers still trace to the ranked feed.

**Shipped.** The three levels already existed; what the audit was objecting
to (§15, §31) was that all three were built from the same card, so the page
still read as one feed with headings in it. Each level now has a different
composition:

| Level | Composition |
|---|---|
| What matters | Full-measure lead (1320px at 1440, 16:9, display-XL headline) + two picture stories |
| What you should know | Two picture stories, then four text-only entries separated by rules |
| More from the world | Two columns of dense headline rows, under the tabs |

The rail moved out from beside the hero, which is what lets the top story take
the full measure — it could not "clearly dominate" while sharing its row with
a statistics panel. §16's standing line (`JUSTNEWS · A clearer tomorrow`) sits
above the greeting.

Measured at 390/768/900/1440/1920 in both themes: axe clean, no horizontal
overflow, composition counts correct at every width (2 hero pictures, 2 + 4 in
tier two, dense rows below). The loading skeleton was updated to match the new
tier-two composition, or the page would jump when the data lands.

**Conflict flagged, not silently resolved.** §16 puts the identity at the top
of Home and §30 puts the same two lines in the footer, so the page now carries
`JUSTNEWS / A clearer tomorrow` twice. That is what both sections ask for, and
it is the normal newspaper masthead-and-colophon pattern, but it is a
duplication the audit did not acknowledge making.

### Chunk 6 — Content normalization *(§20, §21)* — **backend**
Decode HTML entities at ingestion. Detect and trim live-blog furniture
("Updates from…", "Clockwatch", "matchday live", trailing timestamps). Shorten
what the card shows. Repair existing rows with a re-runnable command, like
`repair-edition-times`.
**Accept:** no `&#039;` anywhere; no live-blog string in a snippet; card
snippets read as summaries. Tested on the real production strings above.

**Shipped.** Three rules, each written against a string observed in a live
feed rather than invented:

1. **Entities.** `decode_entities` unescapes **twice**. Production's RSS
   carries `Antonelli&amp;#039;s`: the publisher double-encoded it, feedparser
   resolved one layer, nothing resolved the second. One `html.unescape` was
   never going to fix this. Decoding moved into `normalise_text`, so titles
   get it too — an entity in stored text is an encoding artifact, and
   tokenising, simhashing and the search vector were all working on the wrong
   characters.
2. **Furniture.** `strip_furniture` removes live-blog navigation
   (`Live scoreboard | Clockwatch | Mail Billy 4 min`), the `Updates from
   5.30pm BST kick-off` opener, trailing `— matchday live` markers, the
   Guardian's `Continue reading...` trailer, and its newsletter promo run
   spliced into the middle of the standfirst. Pipes that are the publisher's
   own punctuation survive — there is a test for that, because a rule that
   eats real text is worse than the furniture.
3. **Length.** A second, editorial cap (`ingest_summary_max_chars`, 200)
   under the copyright ceiling (300, unchanged). The cut prefers the *first*
   whole sentence past a 30-character floor, because a publisher's
   `<description>` is usually a standfirst with the article's first paragraph
   glued to the end of it — keeping every sentence that fits keeps half the
   glued paragraph. Sentence detection includes the danda and the Arabic full
   stop, or every Hindi summary would fall through to a mid-word truncation.

`justnews-ingest repair-snippets [--dry-run]` re-cleans the corpus and
recomputes each changed row's search vector. Verified end to end against a
real database: dry run reported one row and wrote nothing, the real run fixed
both the entity and the furniture, and a second run reported zero.

**Still to run against production.** The command has not been pointed at the
production database yet — that is a data change and it is lossy, so it is the
user's call to make.

### Chunk 7 — My Desk as a workspace *(§23–§27)*
Your Topics, What Changed (per-topic developments), Understand (what's
happening / who is saying what / what's changing) from data that exists —
timeline, perspectives, overview. No premature Analysis (§26).
**Accept:** a signed-in desk answers "what changed in my topics" above the
fold; nothing fabricated.

**Shipped.**

*The index.* §24's header, then **What changed** — for each followed topic,
the story cluster whose coverage was most recently added to (`last_seen_at`,
tie-broken by `source_count`; both real columns, no judgement invented here) —
then Your topics. The ordering is the point: the page leads with an answer,
not with navigation. The first entry is set as a lead, per §25's "varied
hierarchy", because the desk is ordered by the reader and the topic they put
first is the one whose news should be biggest.

The section also renders for a signed-out visitor over a few public topics.
§23's complaint is that My Desk is "essentially a sign-in gate", and story
clusters are a public read, so the gate can sit above the page's real answer
rather than in place of it.

*The topic page.* §26's three modules — what's happening (developments by
breadth of coverage), who is saying what (perspectives), what's changing
(timeline) — on one page, as the default view. They were three separate tabs,
which meant a reader had to already know what each held to find any of it.
Those tabs are **removed** rather than duplicated beside Understand; an old
`?tab=timeline` link falls through to Understand, which contains the timeline.
Tabs are now Understand · Latest · Analysis. Analysis is still the honest
stub — §26 says not to build the advanced analysis system prematurely.

Verified with real story-cluster data (seeded locally, since the demo corpus
has none and production has 55 for Politics alone) and with the empty state:
axe clean in both themes at 390/768/1440, no horizontal overflow.

### Chunk 8 — Statistics, search polish, QA *(§22, §28, §40, §45)*
Quiet the glance card to editorial metadata. Search heading and result count.
Then the full matrix again — five widths, both themes, keyboard, reduced
motion, plus performance (§40) which I have not yet measured at all.

**Shipped.**

*§22.* "Today at a glance" was a bordered, filled card with 1.7rem display
numerals — the "generic SaaS dashboard card" the audit names. It is now
option B: a rule and a column of small caps (`29 ARTICLES / 9 SOURCES / 1
LANGUAGE`), the way a newspaper prints its own circulation figures.

*§28.* A `Results` heading and a real count. `SearchPageOut` gained `total`,
counted with the same predicate the listing uses — extracted into
`_search_predicates` so the heading and the list cannot drift apart — and only
on the first page, because recounting the same predicate on page four returns
the same number.

*Pluralisation.* `1 languages` and `1 results` were about to appear in six
places. The repo already had `tPlural`; the strings that needed it did not use
it. `formatCoverage` and the `stats.*` labels are plural-aware now, in all
three locales.

**§40 — measured, not asserted.** Local production build, Chromium:

| Route | LCP | CLS | JS | Fonts | Total |
|---|---|---|---|---|---|
| `/en` | 764–856 ms | **0** | 200 KB | 259 KB | 475 KB |
| `/en/aquila` | 784–948 ms | 0.004 | 134 KB | 208 KB | 360 KB |
| `/hi` | 148 ms | 0 | 200 KB | 495 KB | 710 KB |

CLS is effectively zero everywhere — every image carries width and height, so
nothing reflows on load. Lazy loading is correct: on Home, four of five images
are `loading="lazy"` and the one eager image is the `priority` lead. Images are
hotlinked and `unoptimized`; §40 says not to add server-side image
infrastructure without demonstrating need, and 425 KB across five images with
four of them lazy does not demonstrate it.

**One optimisation tried and deliberately reverted.** The Devanagari UI webfont
downloads on every English and Spanish page — 51 KB, a fifth of the page's font
weight — to draw the six characters of `हिन्दी` in the language switcher.
Dropping `--font-ui-deva` from that one control removed the download and cut
`/en` from 259 KB to 208 KB of fonts. It also rendered the label as five empty
boxes in the measuring browser, which has no Devanagari face installed. "Every
script is a first-class script" does not survive tofu where a language name
should be, so the 51 KB stays, and the reasoning is recorded in the CSS.

**§45 matrix, all clean:** 9 routes × 5 widths (390/768/900/1440/1920) × 2
themes — no horizontal overflow anywhere; axe clean at 390 and 1440 in both
themes. Keyboard: twelve tab stops on Home, every one named, every one with a
2px focus ring. Reduced motion: the paper settles at opacity 1 under both
settings. Backend 476 tests, mypy, ruff check and format green.

---

## 5. Risks

| Risk | Handling |
|---|---|
| Geometry rework breaks composition at some width | Measure at 390/768/900/1440/1920 each time; §38 allows mobile to scroll inside a page |
| Fitting a page may cut stories | Slots-per-page is a composer constant; changing it is reversible and testable |
| Sliding panel is pointer-only | §39 requires a keyboard path; same three-way open as the left edge nav |
| Icon rail loses discoverability | Tooltips plus accessible names; never tooltip-only |
| Content normalization damages good snippets | Repair command with `--dry-run`, and rules matched against real strings |
| Performance unmeasured | §40 gets a real pass in Chunk 8, not an assertion |

## 6. Standing gates

Every chunk: `pnpm typecheck && lint && build`, `uv run pytest`, `mypy`,
`ruff check` **and** `format`, migration round-trip where schema moves,
`make generate-client` when the API surface changes (CI caught this once),
axe in both themes, no overflow at five widths, and — new this pass — a check
against the **live** deployment rather than only the local build.
