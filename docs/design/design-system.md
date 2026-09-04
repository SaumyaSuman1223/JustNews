# Design system — direction

**Status:** direction agreed; visual system revised 2026-09-04 to implement
[`../JustNews_Design_and_Product_Direction.md`](../JustNews_Design_and_Product_Direction.md).
That document is the product and design brief; this one is the system that
implements it and holds the engineering constraints it does not cover.

The site has to survive comparison with the Guardian, Reuters, the FT and
Apple News. That standard is not met with a component library and a blue accent
colour. It is met by getting three things right — typography, hierarchy, and
restraint — and by refusing to let personalisation make the page feel arbitrary.

## Visual identity

**Modern Editorial Minimalism.** A newspaper thoughtfully redesigned for the
digital age — roughly 80% editorial clarity, 20% newspaper character. The
lineage is Swiss/International Typographic Style (grid, objectivity,
asymmetry), Minimalism (reduction), Bauhaus (geometry, function), Plakatstil
(bold headline, negative space), Scandinavian design (calm, restraint) and
classic editorial layout (columns, page hierarchy, pull quotes).

None of these is copied literally. The test for any screen is whether it reads
as *quietly premium, editorial, intelligent and trustworthy* — and whether it
could be mistaken for a SaaS dashboard. If it could, it is wrong.

### One language, three personalities

The three destinations (ADR 0011) share every token and differ in composition
and density, never in visual system.

| Destination | Personality | Reads as |
|---|---|---|
| **Home** | Calm, personal, intelligent | A personal briefing |
| **Aquila** | Editorial, immersive, curated | A published newspaper |
| **My Desk** | Personal, analytical | A research workspace |

Aquila additionally takes a **dark immersive shell** (Deep Charcoal ground,
paper sheet floating in it). This is a route-level surface treatment, not the
application's dark mode; both exist, and the token layer must keep them
separate.

## Principles

**1. The headline is the interface.** On a news site the type *is* the design.
Everything else — rules, spacing, colour — exists to rank headlines against each
other. A reader should be able to tell a lead story from a secondary one without
reading a word.

**2. Density is a feature, not clutter.** Real news sites are dense because
readers scan. The discipline is that density must be *ordered*: a small number of
card sizes, a consistent grid, and clear rails. Airy startup layouts read as
having nothing to say.

**3. Personalised must not mean random.** A feed assembled by a model still has
to look edited. Fixed rails ("Top stories", "Because you read…", "Explore"),
stable slot shapes, and a diversity constraint so the page never becomes eight
cards about the same thing.

**4. Reading is the product.** The article route is the most-visited page and
gets the most design attention: measure, leading, and contrast tuned for
sustained reading, with everything that is not the article subordinate to it.

**5. Every script is a first-class script.** The audience is global, so the
design must hold in Arabic and Chinese as well as it does in English. That is a
constraint on the system, not a translation task: logical CSS properties
everywhere so RTL is a property of the document rather than a stylesheet fork,
per-script font stacks with real coverage, line heights that accommodate
Devanagari and Arabic ascenders and descenders, and no layout that depends on a
string being short — German and Finnish will break it.

**6. Fast is a design property.** A layout that cannot render in under 1.5s on a
mid-range phone is a failed design regardless of how it looks in Figma. Every
component is specified with its skeleton state and its reserved space.

## Foundations

**Typography.** *(Latin-script primary; per-script stacks below.)* A serif for
headlines — it signals journalism and reads better at length — paired with a
sans for UI, metadata and labels. **Cormorant Garamond** for display,
**IBM Plex Sans** for interface. One display family only; a second would read
as indecision. Self-hosted at build time via `next/font` and subsetted, with a
metric-matched fallback so there is no layout shift.

The scale is named by role, not size — Display XL (front-page lead) / Display L
(section) / Display M (story) / Body L / Body M / Body S / Label / Micro — so a
component picks the step for what it *is* and hierarchy cannot drift into
ad-hoc font sizes. Headlines are sentence case or editorial title case; ALL
CAPS is for small letterspaced labels only.

**Colour.** Warm paper and ink, not cool grey. Paper `#F5F1E8` as the ground,
Paper Bright `#FBF9F4` for reading surfaces, Ink `#171717` for text, Warm Gray
`#D8D2C7` for rules and borders, Muted `#77736C` for metadata, Deep Charcoal
`#20211F` for Aquila's immersive shell.

One accent — **Aquila Brass `#A28B68`** — for the active navigation indicator,
edition markers, focus and small editorial highlights. Never as a large fill.
No rainbow category colours, no purple AI gradients. Semantic colours (success,
warning, error, info) stay muted and communicate state only; they are not part
of the decorative palette.

Semantic tokens only (`--surface`, `--surface-raised`, `--text`,
`--text-muted`, `--border`, `--accent`, `--live`, `--danger`) so light and dark
are two values of one system rather than two designs. Every pairing verified at
WCAG AA — 4.5:1 for body, 3:1 for large text and UI boundaries. Warm low-contrast
palettes fail this easily; verify rather than assume.

**Surfaces.** Borders before shadows. `1px solid` warm gray separates; a shadow
is reserved for something genuinely lifted off the page. Radius 0–4px on
editorial surfaces, 6–10px on interface controls, larger only on mobile
touch controls. Not every story is a floating rounded card.

**Script coverage.** A Latin pairing cannot carry Arabic or Chinese. Each script
gets a stack chosen for coverage and rendering quality, matched to the Latin faces
on x-height and weight so a mixed-language feed does not look assembled from
scraps. Arabic and Hebrew need a slightly larger optical size and looser leading
than the Latin default; CJK needs tighter leading and no letter-spacing at all.
These are per-locale token overrides, not per-component fixes.

**Space and grid.** A 4pt base with an 8pt rhythm. All spacing, alignment and
border properties are **logical** (`padding-inline`, `border-inline-start`,
`text-align: start`) so the entire layout mirrors under `dir="rtl"` without a
single directional override. A 12-column desktop grid
collapsing to 6 at tablet and 4 at mobile. Card sizes drawn from a fixed set —
hero, wide, standard, list-row, compact — so any feed the ranker produces still
composes.

**Motion.** Motion explains what changed; it never decorates. Three tiers, one
easing family, decelerating — every transition here reports a state that has
already happened.

| Tier | Duration | For |
|---|---|---|
| Micro | 120–180ms | Hover, icon state, bookmark, toggle |
| Standard | 200–300ms | Navigation, panels, menus, filters, cards |
| Editorial | 350–600ms | Aquila page turns, major content changes, overlays |

No bounce, no floating elements, no parallax, no entrance animations on load.
`prefers-reduced-motion` replaces every editorial-tier transition with a
crossfade and disables the rest — Aquila's page turn must remain fully usable
without it.

**Imagery.** Fixed aspect ratios per card size so images never cause layout
shift, `next/image` with responsive `sizes`, a typographic placeholder when a
source provides no image (common with RSS), and a subtle gradient scrim wherever
text sits over an image.

## Components

Feed: hero card, wide card, standard card, list row, compact row, story-cluster
card ("42 sources covering this"), topic rail, trending ticker, live badge,
section header, ad-slot placeholder (reserved space, unused for now).

Reading: article header with byline and read time, body with pull quotes and
inline media, source attribution block with an outbound link, related-stories
rail, "more from this source", save/share/not-interested actions.

System: left navigation rail (three primary destinations with subtitles, two
secondary, two tertiary), mobile bottom tab bar, top bar with search and
account, footer, command palette (`⌘K`), toast, empty states, skeletons for
every async surface, error states that suggest a next action, and a
cookie/consent banner that is not a dark pattern.

Aquila: masthead, volume/date rule, front-page composition (lead, in-focus
column, the brief, pull quote), section-page templates, page navigation
(prev/next, `1 / 12` indicator, contents panel, page thumbnails), edition
selector, and the paper sheet itself — a warm surface with a subtle
stacked-edge treatment. Never a photographic paper texture and never simulated
page physics; the direction doc rules both out and they read as pastiche.

My Desk: topic tiles (add, remove, reorder), topic header with tabs, timeline
rail, perspective groups (ADR 0013), topic overview, related topics, and an
Analysis placeholder that promises nothing it cannot deliver.

Global surfaces: language and edition switcher as a first-class control in the
header, per-article language badge where it differs from the reader's default,
a "also reported in" affordance on story clusters that spans languages, and
locale-aware date, number and relative-time formatting throughout.

Personalisation surfaces: onboarding topic picker over the 17 IPTC top-level
concepts (expandable to level 2, never 1,200), the exploration deck
(Stage 8), "why am I seeing this?" disclosure on every ranked card, feed-tuning
controls, and a visible exploration slot so discovery is legible rather than
mysterious.

Admin (Stage 4): a deliberately plainer, denser system — data tables, filters,
inline editing, status pills, charts. It shares tokens with the public site but
none of its personality.

## Non-negotiables

- WCAG 2.2 AA, verified by axe in CI, plus a manual keyboard-only pass per route.
- Every interactive element reachable by keyboard with a visible focus ring.
- Dark mode is designed, not derived by inverting.
- Every async surface has a skeleton that reserves the exact final space.
- Zero layout shift after first paint. CLS budget 0.1, enforced in CI.
- Every ranked card can explain itself.
- **Arabic renders correctly with zero locale-specific CSS.** If a fix is needed
  for one locale, the underlying property was physical and should be logical.
- No component assumes a string length. Test with German and with Chinese.
- **No number on screen that does not come from a query.** Reader counts, story
  counts and source counts are computed or absent. A plausible-looking figure
  nobody can trace is a lie with a nice typeface.
- **No article body text.** The product stores title, snippet, image, source,
  author and canonical link, and links out. The story page is a coverage view,
  never a reading view.

## Anti-patterns

The direction document lists these explicitly; they are the failure modes this
system exists to prevent, and any of them appearing is a defect:

generic AI-dashboard aesthetics · purple-blue gradients · glassmorphism ·
everything in a rounded card · card grids as the answer to every layout ·
heavy shadows · large navigation bars · rainbow category colour systems ·
decorative icons · decorative motion · realistic paper textures and fake page
physics · unreadably small "newspaper" type · density without hierarchy.

The last two matter most, because they are what a newspaper-inspired interface
fails into. The reference is a newspaper's *editorial logic* — hierarchy,
columns, rules, restraint — not its physical appearance.
