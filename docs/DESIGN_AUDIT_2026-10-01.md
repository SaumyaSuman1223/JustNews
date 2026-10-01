# JustNews design audit: 2026-10-01 (colour, type, identity)

**The brief:** the owner found the site "stale, off, not very interesting" and asked for an audit of the colour, the fonts and the design overall, with changes.

**Method:**
- Before and after screenshots of 12 routes, against a local production-shaped stack with a fresh ingest of 1,309 articles:
  - both themes at 1440px;
  - phone at 390px;
  - English and Hindi.
- WCAG contrast computed for every token pair.
- Font payloads measured per page.
- The end-to-end suite, including axe on every public route, against a production build.

**The decision:** ADR 0017.

## What was wrong

### 1. It looked like everyone else's AI-made editorial site

- **The look itself.** Cream paper (`#f5f1e8`), a high-contrast display serif (Cormorant Garamond) and one muted warm accent (brass `#a28b68`). That is the look generated "premium editorial" sites converge on. Remove the wordmark and nothing on the page said JustNews.
- **The rules.** The broadsheet hairlines completed the stereotype.

### 2. The headline face was too thin to carry the hierarchy

- **Wrong size range.** Cormorant is a display face with a small x-height and hairline strokes. Most headlines on the site are set at 16-21px: in cards, the rail, Aquila's columns and the story page's coverage rows. There it read faint, and it looked older than the stories it set.
- **No lead.** The lead story and a secondary card differed mainly in size, not in weight or colour, so nothing announced "start here".
- **Wedding invitation.** In the rail and on Aquila the uppercase masthead read like an invitation.

### 3. One beige tone, so nothing separated

- **The ground.** The page, the sidebar, the cards and the rail were all within a few points of the same warm beige.
- **The brass.** To pass AA it had been darkened to `#7a6444`, an olive-khaki. On the primary button it looked disabled. In the Topics card the save button *was* disabled and looked the same as when it worked.

### 4. Cards were boxes, and short ones stretched

- **Stretched boxes.** Each card in a row of three was a bordered white box. A card without a picture kept its row's height, so it stretched into a white panel two-thirds empty.
- **The wrong default.** "Everything in a rounded card" is on `design-system.md`'s own list of anti-patterns.

### 5. Hindi was set in other families

- **What was used:**
  - Hindi headlines in Noto Serif Devanagari;
  - the Hindi interface in Plex Devanagari;
  - beside them, Latin in Cormorant and Plex.
- **The workarounds.** Each script needed a weight correction to sit beside the others.
- **Why it matters.** The product's one structural difference is the same story in several languages on one page, and it looked assembled from three type foundries.
- **Line spacing.** Hindi lead headlines also stood a full line apart. `:lang(hi) { line-height: 1.75 }` applied to the link inside every headline and overrode the headline's own leading.

### 6. Pills and soft corners on every control

Topic chips, the search field, the language buttons and the admin status labels were fully rounded pills. Several interface corners were 8px. Together they made a softer, app-template feel that the type was fighting.

## What changed

| | Before | After |
|---|---|---|
| Headlines and interface | Cormorant Garamond / IBM Plex Sans | **Anek**, one design for Latin and Devanagari. Width carries the hierarchy: 78% for the lead and titles, 86% for headlines, 100% for the interface |
| Reading text | Plex Sans | **Literata** for snippets, decks, How it works and the privacy pages |
| Hindi | Noto Serif Devanagari + Plex Devanagari, a weight lighter | **Anek Devanagari**, the same voice and weight as the English beside it; leading by token, not by blanket `:lang()` |
| Ground / surfaces | Cream `#f5f1e8` everywhere | Porcelain `#f3f3f5` page, white sidebar and panels, blue-black ink text |
| Accent | Brass, accessible as khaki `#7a6444` | **Brand pink**: `#e5196f` mark, `#c4105c` interactive (5.30:1), spent only on the wordmark, where you are, cross-language reach, ranks and Aquila's labels |
| Primary button | Brass fill | Ink fill, pink under the pointer. Disabled is a grey well, so it can't be mistaken for an enabled button |
| Story cards | Bordered white boxes that stretch | No box. A card without a picture stands under a 3px ink rule |
| Controls | Pills, 6-8px corners | 4px corners; editorial surfaces square |
| Sidebar / tabs | Beige fill for the active item; ink underline | A pink bar on the reading-start edge; a pink 3px tab mark |
| Today's Aquila (rail) | A beige paper card | Aquila's own night ground: the rail's one dark object |
| Aquila | Cream sheet, Cormorant uppercase masthead, red labels | Cool newsprint, a condensed heavy nameplate as Hindi and European dailies set one, pink labels |
| Dark theme | Warm charcoal | A designed blue-black night with lifted pinks (6.22:1 and 7.37:1) |
| App icon and share card | Cormorant "JN" on cream | "JN" on ink, the N pink; the share card in the wordmark's own type |

## Cost and checks

**Fonts, English page:**
- Before: 123 KB preloaded (Cormorant ×2, Plex).
- After: Anek Latin, 104 KB preloaded. Literata, 39 KB, is fetched only when needed.
- A 5.5 KB cut draws "हिन्दी" in the language pickers. Without it, English pages would fetch the whole Devanagari file for those six characters.

**Fonts, Hindi page:**
- Before: 283 KB (Plex Devanagari ×2 and Noto Serif Devanagari).
- After: 242 KB, one file. Anek Devanagari is pinned to 90% width with weight left variable; Google serves it only with both axes, at 726 KB.

**Contrast:** every text pairing is AA in both themes, with the ratio noted beside the token in `globals.css`. The lowest are:
- muted text on the sunken surface: 5.20;
- the interactive pink on the pink tint: 4.89;
- control boundaries: 3.2.

**Tests:**
- End-to-end: 29 passed, 3 skipped.
- axe is clean on every route the suite covers.
- Typecheck and lint are clean.

## Not done, or not checked

**Not checked:**
- **Signed-in pages** (Saved, Following, History, Settings, a populated My Desk). They use the same tokens and components, but couldn't be signed into locally.
- **RTL.** It is still unexercised against a real right-to-left locale.

**Not done:**
- **Hindi headline width.** Hindi headlines run at one width (90%), because the file is pinned. A second pinned file at about 80% would let Hindi leads condense like English ones, for about 240 KB more on Hindi pages. That isn't worth it yet.
- **Admin console.** It still sets its headings with inline `fontFamily` styles. It inherits the new faces through the tokens, but those styles should become classes.
