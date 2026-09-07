# Fourth-pass plan

Response to `JUSTNEWS_LATEST_PRODUCT_DESIGN_AUDIT_LOG.md` (logged 8 September
2026), after inspecting the repository and the running application rather than
reading the audit as a to-do list.

---

## 0. What measuring changed

The audit was written against `just-news-pi.vercel.app`. Checked against the
code that actually exists today, most of its body describes work that is
already built and shipped across the second and third passes. That is not a
complaint about the auditor — it is the same pattern the third pass found, and
it matters for the same reason: treating this document as a fresh backlog would
spend the pass rebuilding things that already pass their own acceptance
criteria.

**Already built, and verified in the code today:**

| Audit asks for | Status |
|---|---|
| §3 icon-only rail, 52–60px, keyboard-reachable | 56px, asserted in `e2e/keyboard-nav.spec.ts` |
| §3 Aquila right-edge sliding utility bar, no reflow | `ReaderUtility`, overlay, Escape restores focus |
| §4 Cormorant masthead / IBM Plex UI, 78–100px | Built; measured 86px at a 1175px sheet |
| §5 colour system, ~75/20/5 balance | Tokens, with two documented WCAG deviations |
| §6 paper 1080–1180 × 700–790 at 1440×900, ratio 1.45–1.55 | Re-measured in third-pass Chunk 8: **1174.5 × 783 = 1.500** |
| §7 quote, IN FOCUS, lead, right rail, lower row, highlights, footer | All present; the lower row landed in third-pass Chunk 1 |
| §8 page indicator, arrows, Home/End/Esc, 350–550ms turn, mobile swipe | Built (third-pass Chunk 2 added touch swipe) |
| §9 "do not hardcode NEW DELHI" | Already correct — `DATELINE_CITIES` is deliberately empty and the dateline omits rather than invents |
| §12/§13 three-level Home hierarchy, quiet header | Built |
| §15 statistics as quiet metadata, not dashboard cards | Rule + small caps |
| §16 shortened snippets, no live-blog leakage | Built; the production corpus was repaired |
| §18 cluster counts, timeline | `story_clusters` counts on every card (third-pass Chunk 3), story page (Chunk 4) |
| §19 Lead / Feature / Standard / Brief / Cluster | All five exist; `feature` landed in third-pass Chunk 6 |
| §20 consumer topic names (AI, Markets, Climate…) | Curated presentation layer over IPTC ids (third-pass Chunk 5) |
| §21 recent searches; source, topic, language filters | Built (third-pass Chunk 6) |
| §24 page turn, story expansion, topic unfolding, icon rail | Built (third-pass Chunks 2 and 7) |

**A finding the audit did not make, which may explain the one it did.**

`origin/main` — the repository's default branch — contains exactly one file:
`README.md`. Every workflow (`aquila.yml`, `ingest.yml`, `migrate.yml`,
`uptime.yml`) exists only on `chore/scaffold`.

GitHub Actions runs `schedule:` triggers **only from the default branch's copy
of the workflow file**. With no workflows on `main`, the thrice-daily Aquila
composer (`cron: "7 6,14,22 * * *"`) cannot have fired on schedule, and neither
can the fifteen-minute ingest cron. That is a straightforward mechanical
explanation for §9's P0 observation — a production edition dated 6 September
being served on 8 September is not a rendering bug, it is nothing having
composed an edition since.

Two honesty notes on this. First, I cannot confirm run history from here (`gh`
is not installed), so the mechanism is certain but the consequence is inferred
— the Actions tab settles it in ten seconds. Second, the third-pass plan's §K
asserts "`main` is now the deployed branch and the ingestion cron runs from
it — verified today". Against the repository as it stands, that claim is
false. It is recorded here rather than quietly corrected, because a plan
document asserting something measurement contradicts is precisely the failure
mode these passes keep catching.

**Deferred at your instruction:** §9's stale edition date, and §25's "Aquila
current state" inventory, both of which describe a deployment behind the
branch. The pipeline finding above is filed with them — flagged, not acted on.

---

## Conflicts I will hold, and one I will drop

**Dropping my own previous position: the masthead words.** Third-pass §7 asked
to remove `News · Ideas · People · Perspectives` from Aquila. The
implementation kept the words and made them inert — non-clickable standing
type, with a code comment arguing that furniture is not navigation. This audit
(§10, §25) names the same four words again as the reason Aquila "reads like a
webpage describing a newspaper". Two auditors independently reading the same
compromise the same way is the compromise failing. The words go.

**Holding, for the fourth time: "why it matters".** §12 and §16 both want a
"why it matters" line under the headline. Writing one means either an
editorial voice this product does not have or a model call in the request
path, which ADR 0004 forbids outright. The honest version of that question is
already on the page: how many sources, countries and languages are carrying
the story (§21's diversity line), and who is carrying it (role-grouped
Perspectives, ADR 0013).

**Holding: §7's "2–3 short context paragraphs" and `CONTINUED ON PAGE X`.**
Fourth pass, same answer. `CLAUDE.md` forbids storing article bodies, so there
is no text to continue and none to paraphrase. Page references that point at
real pages are already built and are the honest half of that request.

**Holding: §18's "Different outlets are emphasizing: • …".** That is framing
inference. The verifiable version — grouping a story's sources by their
recorded editorial role — is ADR 0013 and already ships.

**New, and needing your decision: §9's "06:00 AM — Morning".** The audit is
right that `06:00 UTC` is developer output leaking into reader-facing UI. But
its proposed fix assumes one timezone. JustNews publishes one worldwide edition
per language; telling a reader in Tokyo that the Morning Edition was published
at "06:00 AM" is simply false for them. Options in Chunk 2 below.

---

## The chunks

Ordered by correctness first, then by how much of the audit's central
complaint each one answers.

### Chunk 1 — Aquila masthead furniture *(§10, §25)*
Remove `News · Ideas · People · Perspectives`. Replace with masthead furniture
that is true of *this issue*: the sections the issue actually contains, drawn
from `issue.sections`, or the volume/number/dateline line alone if that reads
cleaner at the tested widths. Nothing invented, nothing clickable, nothing that
could be mistaken for site navigation.
**Accept:** no generic category words in the masthead; anything printed there
traces to a column on the issue.

### Chunk 2 — Edition time, told honestly *(§9)*
`aquila.editionTime` is literally `"{time} UTC"` and `IssuePaper` formats with
`timeZone: "UTC"`. Three candidate fixes, in my order of preference:

1. **Edition name carries the identity; the clock goes local.** "Morning
   Edition" stays as the editorial name, and the timestamp renders in the
   reader's own timezone via `Intl`. Honest everywhere, no fabricated claim.
2. **Drop the clock entirely.** Masthead shows the edition name and the date.
   A printed paper does not tell you what time the press ran.
3. **The audit's literal ask** — a fixed "06:00 AM". Rejected unless you want
   it: it states something untrue for most of the world.

Recommend 1, with 2 as the fallback if the local time reads oddly beside the
edition name (a Tokyo reader seeing "Morning Edition · 3:00 PM").
**Accept:** no "UTC" in reader-facing copy; whatever time is shown is true for
the person reading it. **Needs your call before I build it.**

### Chunk 3 — The Daily Brief becomes a brief *(§14)*
Measured: `briefArticles = tierOne.slice(1, 4)` over a three-item tier yields
**two** items, and both are the hero's own supporting stories, printed again a
few hundred pixels below themselves. A brief that repeats the page above it is
not a brief. Fix: draw from stories *outside* the hero tier, take five, and
give it the mini-publication framing §14 asks for — dated, "The world in five
minutes", numbered, one CTA into the issue.
**Accept:** five items, none of them already shown in the Big Three; a date on
the brief; still a list, never a generated summary.

### Chunk 4 — My Desk signed out earns the sign-in *(§20)*
The page already carries real content signed out (What Changed over real
clusters, a curated topic list). What it does not do is say what a desk is
*for* before asking for anything. Add §20's value proposition — follow
subjects, see what changed, compare perspectives, track developments — and one
worked example topic rendered in full, so the value is demonstrated rather
than described.
**Accept:** a signed-out visitor sees one topic's real developments and
perspectives without an account; no line in the pitch describes a capability
that does not ship.

### Chunk 5 — Search grows a date filter and result groups *(§21)*
Three of §21's four filters exist (source, topic, language). Date does not.
Result grouping — Stories / Topics / Sources — does not either, and it is the
part that turns search from a list into a research entry point. Backend: a date
bound threads through the same `_search_predicates` choke point the source
filter already uses; grouping needs topic and source matches alongside article
matches.
**Accept:** every filter's count matches what it returns; a query that matches
a topic or a source says so rather than only returning articles that mention
the word.

### Chunk 6 — A real halftone *(§11)*
Current `Halftone.tsx` is better than the audit assumes — Rec. 709 luminance,
five quantised tonal steps, warm-biased, size-variant dot pitch — and its own
comment is candid that it is "an impression of one". The genuine gap is §11's
core mechanic: **dot size does not vary with tone**. Dark and light regions get
the same grid.

The audit's proposed WebGL route is blocked by the constraint it half-names:
publisher images are cross-origin without CORS headers, and WebGL refuses a
tainted texture at `texImage2D` — you cannot even sample it, let alone read it
back. Server-side processing is out by standing rule. What remains is a pure
SVG filter that thresholds luminance against a tiled dot screen inside the
filter graph — real amplitude modulation, no pixel access, no CORS surface.
**Accept:** measured dot area varies with source luminance; renders in Chromium,
Firefox and WebKit or falls back to today's filter; no new dependency; still
one line to remove. Timeboxed — if the primitive chain does not hold up across
engines, the finding is recorded and the current treatment stays.

**Tried, and reverted.** Built the amplitude-modulation graph: a tiled radial
ramp painted through `feImage href="#screen-rect"` (an in-document `<rect>`
filled by an SVG `<pattern>`), compared against luminance with
`feComposite operator="arithmetic"`, then binarized. The math is sound and
was checked by hand before implementing — but `feImage` referencing local SVG
content by fragment identifier is a long-standing cross-browser weak spot, and
it showed up immediately: in Chromium (the best-supported engine, tested
first) every halftoned image rendered as a flat paper-coloured rectangle, no
photograph and no dots at all — confirmed with `img.complete`/`naturalWidth`
that the source image itself loaded fine, so the failure is in the filter
graph, not the fetch. WebKit could not even be launched in this environment
to check a second engine (missing system libraries for the sandboxed
Playwright install), and Firefox was never reached once Chromium failed the
accept criterion outright. A blank front page is a worse regression than the
fixed dot grid it was replacing, so the change was reverted rather than
shipped and iterated on live. `Halftone.tsx` and the `.halftone` CSS are
unchanged from the third pass. The real fix, if this is picked up again,
almost certainly needs the dot screen supplied as a **data URI**
(`feImage href="data:image/svg+xml,..."`) rather than a same-document
fragment reference — data URIs are `feImage`'s well-supported path — which
this pass did not have the remaining timebox to rebuild and re-verify.

### Chunk 7 — The remaining story types *(§19)*
`Timeline` and `Perspectives` exist as page modules but not as story
compositions a feed can place. `ContextStory` has no honest content source and
is not built. Adds `timeline` and `perspective` variants to the existing
variant set, both fed by data that already ships.
**Accept:** every new variant renders only where its data genuinely exists, and
degrades to an existing variant where it does not.

### Chunk 8 — Rhythm, and the QA matrix *(§22, §23)*
§22 is the audit's actual thesis: heading → content → heading → content reads
as a dashboard. Chunks 1–7 each add one differently-shaped block; this chunk
tunes the sequence across Home and My Desk against §22's
BIG → SMALL → DENSE → SPACIOUS → VISUAL → TEXT → DENSE, then re-runs the full
matrix (9 routes × 5 widths × 2 themes, axe at the extremes, keyboard,
reduced motion, `hi`/`es`) and re-measures performance against the numbers
recorded in the second-pass plan.
**Accept:** no route repeats the same block shape three times running; no
overflow, no axe violation, no performance regression.

---

## Sequencing

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
     ↑
     needs your decision first
```

Chunks 1 and 2 are the audit's P0. Chunks 3–5 are the surfaces it rates
weakest. Chunk 6 is the biggest visual return and the highest technical risk,
which is why it is timeboxed and sits behind the cheaper work. Chunk 8 is last
by definition.

Not in scope, deferred at your instruction: the stale-production Aquila
edition, and the default-branch workflow finding in §0 that probably causes it.
