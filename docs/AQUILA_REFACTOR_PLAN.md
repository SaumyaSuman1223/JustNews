# Aquila-first refactor — implementation plan

Response to `JUSTNEWS_UI_AUDIT_AND_REFACTOR_PLAN_BRIEF.md` (§35 asks for
sections A–J before implementation; §40 asks for inspection first). Written
after inspecting the repository at `e8f59ea`.

## Status — all eight chunks landed

A `ded9594`/`081532d` · B `45b318e`/`104fec9` (+`2703287`) · C `4de8f80`/`81dd4b5` ·
D `e7effac` · E `d118678` · F `28c54ab` · G `ecbab95`/`1db9858` · H — this commit.

Where the plan was wrong, and what happened instead:

- **Chunk A's masthead.** I judged the three-column header impossible at a
  600px content box and stacked it. Chunk B's escape from the app shell widened
  the sheet to ~900px, and it was restored there. The plan should have
  sequenced the container before judging what fits inside it.
- **Chunk E's fidelity risk** did not materialise. The CSS/SVG halftone was
  judged good enough by looking at it, so the cached-pipeline escalation and
  the ADR it would have required were not needed.
- **Chunk C grew** an image-aware composer, because an editorial grid that
  prints pictures is worthless if selection ignores whether an article has one.
- §36's matrix runs green: five widths, both themes, five routes, keyboard,
  reduced motion. See the Chunk H commit for the full record.

---

## A. Current architecture

| Layer | State |
|---|---|
| Web | Next.js App Router, `frontend/app/[locale]/…`, one shell layout for every route |
| Aquila data | `issues` / `issue_pages` / `issue_slots`, composed offline (ADR 0012) |
| Composer | `apps/ingestion/src/justnews_ingestion/aquila.py`, cron 06/14/22 UTC |
| Aquila API | `GET /v1/issues/latest`, `/{id}`, `/{id}/pages/{n}`, `/editions` |
| Aquila UI | `IssueReader.tsx` (client, page turns) + `IssuePaper.tsx` (one page) |
| Slot roles | `lead` \| `secondary` \| `brief` (CHECK on `issue_slots.role`) |
| Fonts | Cormorant Garamond (display) + IBM Plex Sans (UI), + Devanagari pair |
| Images | Publisher CDN URLs, hotlinked, `next/image unoptimized`. No processing. |

## B. Problems — verified against the code, not assumed

**Real, confirmed:**

1. **Edition time is wall-clock, not the slot.** `aquila.py:280` sets
   `published_at=now`, the moment the composer happened to run. That is
   literally the "4:47 PM Midday Edition" in §11. One-line fix.
2. **Aquila renders inside the normal app shell.** `[locale]/layout.tsx`
   wraps every route in `.shell` with the sidebar; Aquila is a route, not a
   reader (§7, §22, §30).
3. **No halftone anywhere** (§19).
4. **One image per Aquila page.** `IssuePaper.tsx` renders an image only for
   the lead, and the composer never looks at `image_url` when selecting — an
   image slot can land on an article that has none (§15, §19).
5. **Masthead identity is wrong.** Renders "The Aquila Tribune" (hardcoded)
   with strap "A clearer tomorrow, together". Brief wants **AQUILA TRIBUNE** /
   **THE WORLD IN CONTEXT** in a three-column header (§9, §10).
6. **No editorial grid.** The front page is a generic 3-column container
   query, not left-rail / dominant lead / varied right rail / lower row (§14, §15).
7. **Search is minimal** — no filters, no recent searches (§29).

**Already satisfied — the audit's concern does not apply:**

- **Samarkan is referenced nowhere in code.** It is an unused file in
  `docs/samarkan-font/`. The non-negotiable is already met.
- **The edition source of truth already exists.** `Issue.published_on`
  (edition_date), `edition_slot` (edition_type), `published_at` — exactly §12's
  three concepts. `list_editions` already anchors to the latest issue's day
  rather than "today", so a 02:00 reader correctly gets last night's paper.
  Only the `published_at` *value* is wrong. **No backend redesign needed.**
- **06/14/22 is already the schedule** — `EDITION_SLOTS` and `aquila.yml`.
  Only the displayed time was wrong.
- **Volume/number are deterministic** (volume = year − 2025, number = ordinal
  within volume). The "Vol. 1 No. 1" in the audit is correct output, not drift.
- **`News · Ideas · People · Perspectives` is not navigation.** It is a static
  masthead standfirst line. §6 bans it as *app* navigation; §10 wants exactly
  those words as newspaper furniture in the header's top-right. So it moves,
  it does not get deleted.

**Out of date in the audit:**

- **"My Desk is primarily a sign-in gate"** — the workspace behind auth was
  built in Chunks 5–6: topic tiles with reorder, Latest/Timeline/Key
  Developments/Perspectives tabs, topic overview and related topics. The
  auditor saw the signed-out gate. My Desk needs *polish*, not construction.

**Conflicts with this repo's own hard rules — flagged, not silently resolved:**

- §15 asks the lead for **"2–3 short context paragraphs"** and
  **"CONTINUED ON PAGE 2"**. JustNews stores title + snippet (≤300 chars) and
  never body text (CLAUDE.md). There is no text to continue and no paragraphs
  to print. Adaptation: the snippet becomes the deck; page references appear
  only where a real page exists. Fake continuation lines are not shippable.
- §10's **"NEW DELHI"** dateline is a hardcoded city in a global, multilingual
  product. **Decided:** derive the city from the edition's locale/configuration
  where one is reliably available; where it is not, print the date line without
  a city rather than inventing one. No hardcoded "NEW DELHI".
- §17's **red section labels** + §18's `#A52E2A` introduce an accent distinct
  from the app's brass `#7a6444`. Legitimate as a route-scoped surface
  treatment (same precedent as Aquila's dark workspace), but it must be
  Aquila-scoped and contrast-verified.
- §9's masthead at **78–100px** contradicts the earlier pixel spec's 70–90px
  masthead *block*. The newer brief wins for Aquila; I will note the override.

## C. Proposed architecture

```
app/[locale]/layout.tsx          → html, fonts, session, consent (no visual shell)
  (app)/layout.tsx               → the shell: rail, mobile tabs, footer
    page.tsx, desk/, search/, saved/, story/, a/, settings/ …
  (reader)/layout.tsx            → dark workspace, no shell
    aquila/page.tsx
```

Route groups do not change URLs. Aquila escapes the shell; everything else is
untouched by the move.

New: `focus` slot role (the IN FOCUS left-rail item), image-aware composer
selection, an Aquila-scoped token block, an SVG halftone filter.

## D. Reuse strategy — what is not touched

Backend architecture, database, auth, recommendation/ranking, ingestion,
content pipeline, admin, data models, deployment. The only backend changes are
one wrong value (`published_at`), one widened CHECK (`role`), and composer
selection preferring image-bearing articles for image slots. Everything in
§32's do-not-touch list stays.

## E. Migration strategy

Each chunk lands green and deployable on its own. Aquila's data contract is
additive (`focus` role widens a CHECK; existing rows stay valid). The route
group move is mechanical `git mv` with no logic change. The halftone is a
route-scoped CSS filter, so a bad result is reverted by deleting one rule and
cannot damage non-Aquila images.

## F. File-level plan

| Change | Files |
|---|---|
| Edition time | `aquila.py` (~1 line), backfill script for existing rows |
| Masthead/header | `IssuePaper.tsx`, `i18n.ts`, `globals.css` |
| Reader shell | `layout.tsx` → `(app)/` + `(reader)/`, ~15 route dirs moved, new `AquilaSidebar.tsx` |
| Editorial grid | `IssuePaper.tsx`, `globals.css`, `aquila.py` (roles/counts) |
| `focus` role | migration `0016`, `models.py`, `aquila.py` |
| Halftone | `globals.css`, new `Halftone.tsx` (SVG defs), `IssuePaper.tsx` |
| Home tiers | `app/[locale]/page.tsx`, `FeedList.tsx`, `globals.css` |
| Search | `app/[locale]/search/page.tsx`, `SearchBox.tsx` |

## G. Phased implementation

Eight chunks. Each lands green, deployable, and independently revertable.
Ordered so the container exists before the thing built inside it: A is small
and kills two bugs visible on the live site today; B establishes the reader
container; C–E build the newspaper inside it; F–H work outward from there.

---

### Chunk A — Edition truth and masthead identity

*Brief §9–§12. Small. Highest visible-bug-per-line ratio in the programme.*

The composer stamps `published_at=now` — the minute the cron happened to run.
That is the "4:47 PM Midday Edition" the audit saw. The slot already carries
the intended hour in `EDITION_SLOTS`; the fix is to use it.

**Work**
1. `aquila.py`: build `published_at` from `published_on` + the slot's hour in
   UTC, not `now`. `now` stays for volume computation only.
2. One-shot backfill for existing rows — derive from `published_on` +
   `edition_slot`. Ships as a script under `apps/ingestion`, not a migration:
   it is data repair, not schema, and must be re-runnable.
3. Masthead identity in `IssuePaper.tsx` + `i18n.ts`:
   **AQUILA TRIBUNE** / **THE WORLD IN CONTEXT**, three-column header —
   left: edition slot + volume/number; centre: wordmark + strap; right:
   `News · Ideas · People · Perspectives` (moved here from standfirst, not
   deleted — §10 wants exactly those words as furniture).
4. Dateline: city derived from the edition's locale/configuration when
   reliably available, else date only. A `localeCity` lookup that returns
   `null` by default, not a hardcoded string.
5. Edition selector restrained to a text rule, not a control cluster (§11).
6. Masthead set in Cormorant Garamond heavy, 78–100px, tight tracking.

**Files** `aquila.py`, new `backfill_edition_times.py`, `IssuePaper.tsx`,
`i18n.ts` (×3 locales), `globals.css`
**Accept** A midday issue reads `MIDDAY EDITION · 14:00 UTC` regardless of when
the cron ran. No issue displays a wall-clock time. No "NEW DELHI" in the tree.
Composer test asserts `published_at.hour == EDITION_SLOTS[slot]`.
**Risk** Low. One value, additive backfill.

---

### Chunk B — The full-screen reader shell

*Brief §7, §22, §30. The container. Nothing after this is built twice.*

Aquila currently renders inside `.shell` — sidebar, mobile tab bar, footer.
A newspaper cannot feel like a newspaper while wearing an app chrome.

**Work**
1. Route groups. `app/[locale]/layout.tsx` keeps html/fonts/session/consent
   and loses the visual shell. New `(app)/layout.tsx` holds the shell as it
   is today; new `(reader)/layout.tsx` holds the dark workspace.
   `git mv` the 16 non-Aquila route dirs into `(app)/`, `aquila/` into
   `(reader)/`. **Route groups do not change URLs** — zero redirects needed.
2. `AquilaSidebar.tsx`: edge-triggered, hidden at rest, revealed on hover
   near the viewport edge or on `Escape`-toggled focus. Never permanent.
3. Contents overlay — issue's pages and sections, keyboard-reachable.
4. Keyboard: `←`/`→` page turn (RTL-flipped), `c` contents, `Esc` close.

**Files** `layout.tsx` split into 3, ~17 route dirs moved, new
`AquilaSidebar.tsx`, `AquilaContents.tsx`, `globals.css`
**Accept** Every existing URL resolves unchanged (e2e suite is the proof).
Aquila renders edge-to-edge with no app chrome. Full keyboard traverse of an
issue without a mouse. axe clean, both themes.
**Risk** Medium — a large mechanical move. Mitigation: the move commit
contains *only* `git mv` and import-path fixes, no logic, so a bisect is
unambiguous.

---

### Chunk C — Editorial grid and composition

*Brief §14, §15. The front page stops being a card container.*

Two halves: the composer must **select** for a newspaper, and the page must
**lay out** like one. Doing only the second gives a beautiful grid with an
image slot on an article that has no image.

**Work**
1. Migration `0016`: widen `issue_slots.role` CHECK to include `focus`.
   Additive — every existing row stays valid.
2. `aquila.py`: image-aware selection. Slots that will render an image prefer
   articles with `image_url`; a `focus` slot is chosen for the left rail.
   Selection stays deterministic and diversity-constrained as it is today.
3. `IssuePaper.tsx` rebuilt to the real grid: left rail (IN FOCUS) ·
   dominant lead · varied right rail · lower row. Not a uniform 3-column
   container query.
4. TODAY'S HIGHLIGHTS band.
5. **Adaptation, flagged:** §15's "2–3 context paragraphs" and "CONTINUED ON
   PAGE 2" have no source data — the repo never stores body text. The snippet
   becomes the deck; a page reference is printed **only** where that story
   genuinely continues on a later page of this issue.

**Files** migration `0016`, `models.py`, `aquila.py`, `IssuePaper.tsx`,
`globals.css`, composer tests
**Accept** Migration `base→head→base→head` clean. No image slot renders a
missing image. Front page holds four distinct compositional zones at
≥1280px, degrades to one column at 390px without squeezing (§24). No
continuation line points at a page that does not exist.
**Risk** Medium — long headlines in a fixed grid. Long-headline fixtures in
the composer tests, per §9.

---

### Chunk D — Typography and colour

*Brief §17, §18.*

**Work** Aquila-scoped type scale; red section labels at `#A52E2A` scoped to
the reader group only — the app keeps brass `#7a6444`; rules and hairlines as
structure rather than borders-on-cards.
**Files** `globals.css`, `IssuePaper.tsx`
**Accept** `#A52E2A` appears under no `(app)` selector. Contrast verified on
the Aquila ground in both themes — axe zero violations, and the red measured
directly, since axe will not catch a decorative label it treats as ineligible.
**Risk** Low, and contained: a route-scoped token block.

---

### Chunk E — Halftone

*Brief §19. Isolated deliberately so a bad result is one revert.*

**Work** `Halftone.tsx` — an inline SVG `<filter>` (`feImage`/`feTile` dot
screen + `feColorMatrix` desaturation), applied to Aquila images only via a
route-scoped class. Images stay hotlinked from the publisher CDN; nothing is
re-encoded and nothing is stored.
**Files** new `Halftone.tsx`, `globals.css`, `IssuePaper.tsx`
**Accept** Every Aquila image carries identical treatment. Zero publisher
images re-hosted. Reverting = deleting one CSS rule. Non-Aquila images
provably untouched.
**Risk** Medium on *fidelity* — CSS/SVG halftone has a quality ceiling. Look
at it before committing. If genuinely insufficient, that escalation needs an
ADR, because a server-side pipeline means storing derivatives of publisher
images and that crosses a product rule.

---

### Chunk F — Home's three-level hierarchy

*Brief §2, §26. First chunk outside Aquila.*

**Work** Home restructured into *What matters* / *What you should know* /
*What else is happening*, replacing the flat hero+rail+tabs stack. Reuses
the existing ranked feed — this is presentation, not ranking.
**Files** `(app)/page.tsx`, `FeedList.tsx`, `HomeSkeleton.tsx`, `globals.css`
**Accept** Three visually distinct tiers. `HomeSkeleton` matches the new grid
(the CLS discipline from Chunk 7 holds). Every number still traces to a query.
**Risk** Low.

---

### Chunk G — My Desk polish and Search

*Brief §28, §29. Scoped down deliberately.*

The audit's "My Desk is primarily a sign-in gate" is **out of date** — the
workspace was built in Chunks 5–6. This is polish, not construction:
signed-out state that shows what the desk *is*, tighter tile rhythm, and
Search gaining filters (topic, language, date) and recent searches.

**Files** `(app)/desk/**`, `(app)/search/page.tsx`, `SearchBox.tsx`,
`DeskTiles.tsx`, `globals.css`
**Accept** Signed-out desk previews real value. Search filters map to
existing endpoint params — no new backend.
**Risk** Low.

---

### Chunk H — Print character, motion, QA matrix

*Brief §20, §21, §24, §34.*

**Work** Print details (rules, drop caps where a real deck exists, tabular
figures); page-turn motion at `--dur-editorial` with a working
`prefers-reduced-motion` crossfade; the full §36 matrix across
390/900/1280/1440/1920 in both themes.
**Accept** §36's list, green.
**Risk** Low.

## H. Dependencies

**None. Confirmed.** Cormorant Garamond is already loaded and is on §9's
approved list; **Bodoni Moda is explicitly rejected** — the masthead is set in
Cormorant Garamond at heavy weight with tightened tracking. The repo keeps one
serif + one sans, and the font budget does not grow.

The halftone is an inline SVG filter — no `sharp`, no image service, no new
package.

## I. Risk assessment

| Risk | Severity | Handling |
|---|---|---|
| Re-hosting publisher images for halftone | **High** (ToS/legal + free-tier cost + contradicts "always link out") | Avoided: CSS/SVG filter on hotlinked images. No derivative stored. |
| Halftone fidelity ceiling with CSS | Medium | Look at it before committing to it; escalate to a cached pipeline only via ADR if genuinely insufficient. |
| Route group move breaks a route | Medium | URLs are unchanged by route groups; e2e suite covers every locale route. |
| Newspaper layout at tablet/mobile | Medium | §24 already says do not squeeze — one page, scroll inside, swipe between. |
| Edition backfill | Low | Existing rows get slot-derived `published_at`; `published_on` already correct. |
| Aquila accent contrast on cream | Low | axe on every Aquila surface, both themes, as every chunk this session has. |
| Fixed newspaper height vs. long headlines | Medium | Composer already caps counts; test with long-headline fixtures per §9. |

## J. Acceptance criteria

Per-chunk criteria are stated inline in section G, under each chunk's
**Accept** line. They are the gate for that chunk, not a summary of it.

Standing gates every chunk must clear regardless: §36's list, plus this repo's
standing gates — `pnpm typecheck && lint && build`, `uv run pytest`, `mypy`,
`ruff`, migration `base→head→base→head`, `alembic check`, axe zero violations
light **and** dark, no horizontal overflow at 390/900/1280/1440/1920.
