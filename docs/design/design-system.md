# Design system — direction

**Status:** direction agreed, visual design produced in Stage 3.

The site has to survive comparison with the Guardian, Reuters, the FT and
Apple News. That standard is not met with a component library and a blue accent
colour. It is met by getting three things right — typography, hierarchy, and
restraint — and by refusing to let personalisation make the page feel arbitrary.

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

**Typography.** *(Latin-script primary; per-script stacks below.)* A serif for headlines and article body — it signals journalism
and reads better at length — paired with a geometric sans for UI, metadata and
labels. Variable fonts, subsetted, self-hosted, `font-display: swap` with a
metric-matched fallback so there is no layout shift. A modular type scale with
distinct steps for lead / section-lead / card / list / meta, so hierarchy is
structural rather than ad hoc.

**Colour.** Near-black on off-white, not pure black on pure white. One accent,
used for links, focus and live indicators, and nowhere else. Semantic tokens
only (`--surface`, `--surface-raised`, `--text`, `--text-muted`, `--border`,
`--accent`, `--live`, `--danger`) so light and dark are two values of one
system rather than two designs. Every pairing verified at WCAG AA — 4.5:1 for
body, 3:1 for large text and UI boundaries.

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

**Motion.** Almost none. Fades and small translations under 200 ms for state
changes, a considered page transition on the article route, nothing decorative.
`prefers-reduced-motion` disables all of it.

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

System: header with search and account, mega-menu topic navigation, footer,
command palette (`⌘K`), toast, empty states, skeletons for every async surface,
error states that suggest a next action, and a cookie/consent banner that is not
a dark pattern.

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
