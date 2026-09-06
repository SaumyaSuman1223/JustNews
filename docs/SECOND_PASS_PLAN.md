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

### Chunk 3 — Aquila utility bar and editorial right rail *(§12, §13)*
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

### Chunk 5 — Home composition *(§15–§19, §31, §32)*
The Big Three (one dominant + two), then a varied grid for What You Should
Know, then More From The World. Break the repeated card rhythm: alternate
image-left/right, text-dominant entries, varied headline weight.
**Accept:** no two adjacent sections use the same composition; first story
dominates unmistakably; three tiers still trace to the ranked feed.

### Chunk 6 — Content normalization *(§20, §21)* — **backend**
Decode HTML entities at ingestion. Detect and trim live-blog furniture
("Updates from…", "Clockwatch", "matchday live", trailing timestamps). Shorten
what the card shows. Repair existing rows with a re-runnable command, like
`repair-edition-times`.
**Accept:** no `&#039;` anywhere; no live-blog string in a snippet; card
snippets read as summaries. Tested on the real production strings above.

### Chunk 7 — My Desk as a workspace *(§23–§27)*
Your Topics, What Changed (per-topic developments), Understand (what's
happening / who is saying what / what's changing) from data that exists —
timeline, perspectives, overview. No premature Analysis (§26).
**Accept:** a signed-in desk answers "what changed in my topics" above the
fold; nothing fabricated.

### Chunk 8 — Statistics, search polish, QA *(§22, §28, §40, §45)*
Quiet the glance card to editorial metadata. Search heading and result count.
Then the full matrix again — five widths, both themes, keyboard, reduced
motion, plus performance (§40) which I have not yet measured at all.

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
