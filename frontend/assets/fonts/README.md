# Fonts

Served from this repository so a build never depends on reaching Google Fonts
(lib/fonts.ts). The files are Google Fonts' own subsets, split by
unicode-range: `latin`, `latin-ext` and `devanagari`.

| Family                   | Files                                                                                                                           | Licence                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Cormorant Garamond       | `web/cormorant-*` (variable, 300-700, normal and italic); `CormorantGaramond-600-latin.ttf` for generated images (lib/icon.tsx) | SIL OFL 1.1 (`OFL-CormorantGaramond.txt`)   |
| IBM Plex Sans            | `web/plex-latin*` (variable, 100-700)                                                                                           | SIL OFL 1.1 (`OFL-IBMPlex.txt`)             |
| IBM Plex Sans Devanagari | `web/plex-deva-*` (400, 600)                                                                                                    | SIL OFL 1.1 (`OFL-IBMPlex.txt`)             |
| Noto Serif Devanagari    | `web/noto-serif-deva-*` (variable, 100-900)                                                                                     | SIL OFL 1.1 (`OFL-NotoSerifDevanagari.txt`) |

To update one, download the family's CSS from
`https://fonts.googleapis.com/css2?family=...` with a current browser's
user agent and replace the matching `woff2` files.
