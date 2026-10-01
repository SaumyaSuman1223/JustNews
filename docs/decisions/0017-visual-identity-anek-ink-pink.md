# 0017 — Visual identity: Anek and Literata, ink on porcelain, one brand pink

- **Date:** 2026-10-01
- **Status:** accepted. Replaces the typography and colour sections of `docs/design/design-system.md` (2026-09-04).

## Context

The site was set in Cormorant Garamond for headlines and IBM Plex Sans for the interface, on warm cream paper (`#f5f1e8`), with a brass accent (`#a28b68`). The owner's verdict on it was "stale, off, not very interesting". The design audit (`docs/DESIGN_AUDIT_2026-10-01.md`) found why:

- **It was the default look.** Cream ground, a high-contrast display serif and one muted warm accent is the look AI-generated editorial sites converge on. Nothing in it said JustNews.
- **Cormorant failed at interface sizes.** It is a thin, low-x-height display face. The card headlines, rail lists and Aquila's columns (16-21px) are where most headlines on the site actually appear, and there it read faint and old-fashioned. Lead stories and secondary stories barely differed in weight.
- **Everything shared one tone.** The page, the sidebar and the cards were all beige, so nothing separated them. The brass, measured down to an accessible `#7a6444`, made the primary button look disabled.
- **Hindi was set in other families.** Noto Serif Devanagari for headlines and Plex Devanagari for the interface, each corrected a weight step to sit beside the Latin. That is the product's one structural difference from Google News, Apple News and Ground News: the same story in several languages on one page. It was set as if assembled from three foundries.

## Options

1. **Refine the incumbent.** A darker brass, a heavier Cormorant cut. This keeps the default look and the thin interface sizes.
2. **A conventional news sans with a blue accent.** Safe, and indistinguishable from every news app. `design-system.md` itself rules out "a component library and a blue accent colour".
3. **A multi-script family as the voice, condensed for headlines; a reading serif for text; ink on a cool porcelain ground; one saturated brand colour spent only on what is JustNews's own.**

## Decision

Option 3.

- **Anek** (Ek Type; SIL OFL) for headlines and the interface.
  - One design drawn for Latin and Devanagari together, so an English and a Hindi headline share a voice.
  - Its width axis carries the hierarchy:
    - the lead, page titles and mastheads at 78% width, weight 720;
    - other headlines at 86%, weight 620;
    - the interface at 100%.
  - Condensed heavy headlines are how Hindi dailies and many European papers set news, so the face suits the subject, not just the brand.
- **Literata** (TypeTogether for Google; SIL OFL) for reading text: snippets, decks, long-form pages and Aquila's decks.
- **Palette.**
  - Ground: porcelain `#f3f3f5`. Surfaces: `#ffffff`. Text: blue-black ink `#12131c`.
  - Dark theme: a designed blue-black night (`#0e0f15`), not an inversion.
- **One brand pink.**
  - Values:
    - `--mark` `#e5196f`, for large or decorative use;
    - `--accent` `#c4105c`, for links, focus and active labels, at 5.30:1 on the ground.
  - Dark-theme values: `#ff4f98` and `#ff6fa8`.
  - Why pink: it is the colour both of the product's non-English audiences claim, *rani* pink in Hindi and *rosa mexicano* in Spanish.
  - Where it is spent:
    - the wordmark's "News";
    - where you are (active sidebar and tab marks);
    - a story's reach across languages;
    - the most-read ranks;
    - Aquila's section labels.
  - Primary buttons are ink, turning pink on hover.
- **Surfaces.**
  - Story cards lose their box. A card without a picture stands under a 3px ink rule where the picture's edge would be.
  - Controls take a 4px corner; nothing is a pill.
  - Today's Aquila teaser in the rail is set on Aquila's own night ground, the rail's one dark object.

## Consequences

**Weight.**
- Anek Devanagari is served only with both axes, at 726 KB. Pinned to 90% width with weight left variable, it is 242 KB. That is less than the Plex Devanagari pair plus Noto Serif Devanagari it replaces (283 KB), and it now serves Hindi headlines, interface and reading text.
- Hindi headlines therefore have one width.
- English pages draw "हिन्दी" in language pickers from a 5.5 KB cut of the same face, so they never fetch the Devanagari file.
- An English page preloads Anek Latin (104 KB) and fetches Literata (39 KB) on demand. Before, it preloaded 123 KB of Cormorant and Plex.

**Accessibility.** Every text pairing is AA in both themes; the ratios are recorded beside the tokens in `globals.css`. Axe is clean on every route.

**Leading.** Hindi leading moved from `:lang(hi)` to the `lang` attribute. `:lang()` matched every descendant and overrode each headline's own leading.

**Generated images.** The app icon, favicon and share card use two static TrueType instances of Anek, because the image renderer reads only TrueType.

**What did not change.** Aquila keeps its sheet, its page turn and its layouts. Its paper moves from cream to a cool newsprint (`#f7f7f4`) and its accent from red to the brand pink, so the newspaper and the app are one identity.
