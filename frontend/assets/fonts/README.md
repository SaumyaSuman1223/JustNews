# Fonts

Served from this repository so a build never depends on reaching Google Fonts
(lib/fonts.ts, ADR 0017). The files are Google Fonts' own subsets, split by
unicode-range: `latin`, `latin-ext` and `devanagari`.

| Family          | Files                                                                                                                                                               | Licence                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| Anek Latin      | `web/anek-latin-*` (variable, width 75-125%, weight 100-800); `AnekLatin-Condensed-800-latin.ttf` and `AnekLatin-400-latin.ttf` for generated images (lib/icon.tsx) | SIL OFL 1.1 (`OFL-AnekLatin.txt`)      |
| Anek Devanagari | `web/anek-deva-devanagari-90-400-750.woff2` (width pinned at 90%, weight 400-750); `web/anek-deva-endonym-*` ("हिन्दी" only, for language pickers)                  | SIL OFL 1.1 (`OFL-AnekDevanagari.txt`) |
| Literata        | `web/literata-*` (variable, weight 400-700, normal and italic)                                                                                                      | SIL OFL 1.1 (`OFL-Literata.txt`)       |

To update one, download the family's CSS from
`https://fonts.googleapis.com/css2?family=...` with a current browser's user
agent and replace the matching `woff2` files.

Four files are derived rather than downloaded, with fontTools
(`uvx --from 'fonttools[woff]' ...`):

- **Anek Devanagari:** Google serves it only with both axes, at 726 KB.
  `fontTools.varLib.instancer.instantiateVariableFont(font, {"wdth": 90, "wght": (400, 750)})`,
  saved as WOFF2, is 242 KB.
- **The endonym cut:** `pyftsubset <that file> --text="हिन्दी" --layout-features='*' --flavor=woff2`.
- **The two TrueType files** (the image renderer reads TrueType only): the
  Latin WOFF2 instanced at width 75 / weight 800 and at width 100 / weight
  400, saved unflavoured.
