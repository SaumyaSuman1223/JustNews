/**
 * The product's two typefaces, served from files in this repository
 * (assets/fonts/web) - Google Fonts' own subsets, by unicode-range, so a
 * build never depends on reaching Google (ADR 0017).
 *
 * - **Anek** (Ek Type) sets headlines and the interface. It is one design
 *   drawn for Latin and Devanagari together, so an English and a Hindi
 *   headline on the same page share a voice instead of looking assembled
 *   from two foundries - which is what a cross-language news reader puts
 *   side by side all day. Its width axis carries the hierarchy: headlines
 *   run condensed, the interface at normal width (globals.css --stretch-*).
 * - **Literata** sets reading text: decks, snippets, long-form pages.
 *
 * Each script's subset is its own family, so a page fetches only the ranges
 * its text uses: an English page never downloads the Devanagari file, and
 * the extended-Latin file arrives only for a name like "Erdoğan". The
 * metric-matched fallback that keeps the swap from shifting layout sits on
 * the second family in each stack (the first carries none), so it comes
 * after the basic-Latin face and before any other script's.
 *
 * The Devanagari file is Anek Devanagari pinned at 90% width with weight
 * left variable (fontTools' instancer): the full width-and-weight file is
 * 726 KB, the pinned one 242 KB - less than the two Plex Devanagari weights
 * and Noto Serif Devanagari it replaces. Hindi headlines and interface share
 * that one width.
 *
 * Licences: SIL Open Font License 1.1 (assets/fonts/README.md). The
 * unicode-ranges are written out in each call because next/font takes only
 * literal values; they are Google's own ranges for each subset.
 */
import localFont from "next/font/local";

/** Headlines and interface, basic Latin. Variable: width 75-125%, weight
 * 100-800. Preloaded - every page's first headline is set in it. */
export const sans = localFont({
  src: [
    {
      path: "../assets/fonts/web/anek-latin-latin-75-125-100-800.woff2",
      weight: "100 800",
      style: "normal",
    },
  ],
  display: "swap",
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
    },
    { prop: "font-stretch", value: "75% 125%" },
  ],
  adjustFontFallback: false,
  variable: "--font-sans-latin",
});

export const sansExt = localFont({
  src: [
    {
      path: "../assets/fonts/web/anek-latin-latin-ext-75-125-100-800.woff2",
      weight: "100 800",
      style: "normal",
    },
  ],
  display: "swap",
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
    },
    { prop: "font-stretch", value: "75% 125%" },
  ],
  adjustFontFallback: "Arial",
  variable: "--font-sans-latin-ext",
});

/** Headlines, interface and reading text in Devanagari: one file, 90%
 * width, weight 400-750. */
export const sansDevanagari = localFont({
  src: [
    {
      path: "../assets/fonts/web/anek-deva-devanagari-90-400-750.woff2",
      weight: "400 750",
      style: "normal",
    },
  ],
  display: "swap",
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0900-097F, U+1CD0-1CF9, U+200C-200D, U+20A8, U+20B9, U+20F0, U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B09",
    },
  ],
  adjustFontFallback: "Arial",
  variable: "--font-sans-deva",
});

/** "हिन्दी" and nothing else, cut from the file above (5.5 KB): language
 * pickers name each language in its own script, so every English page draws
 * those six characters, and the whole Devanagari file is not worth that.
 * Used only by picker labels (globals.css --font-endonym), never in the
 * general stack - mixing it into running Hindi would split syllables across
 * two files, which some browsers shape as separate letters. */
export const endonym = localFont({
  src: [
    {
      path: "../assets/fonts/web/anek-deva-endonym-90-400-750.woff2",
      weight: "400 750",
      style: "normal",
    },
  ],
  display: "swap",
  preload: false,
  declarations: [
    { prop: "unicode-range", value: "U+0926, U+0928, U+0939, U+093F, U+0940, U+094D" },
  ],
  adjustFontFallback: false,
  variable: "--font-endonym-deva",
});

/** Reading text, basic Latin. Variable weight 400-700, with its italic. Not
 * preloaded: the first thing a page paints is a headline, and the
 * metric-matched fallback holds the deck's space until this arrives. */
export const serif = localFont({
  src: [
    {
      path: "../assets/fonts/web/literata-latin-normal-400-700.woff2",
      weight: "400 700",
      style: "normal",
    },
    {
      path: "../assets/fonts/web/literata-latin-italic-400-700.woff2",
      weight: "400 700",
      style: "italic",
    },
  ],
  display: "swap",
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
    },
  ],
  adjustFontFallback: false,
  variable: "--font-serif-latin",
});

export const serifExt = localFont({
  src: [
    {
      path: "../assets/fonts/web/literata-latin-ext-normal-400-700.woff2",
      weight: "400 700",
      style: "normal",
    },
    {
      path: "../assets/fonts/web/literata-latin-ext-italic-400-700.woff2",
      weight: "400 700",
      style: "italic",
    },
  ],
  display: "swap",
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
    },
  ],
  adjustFontFallback: "Times New Roman",
  variable: "--font-serif-latin-ext",
});

/** Every font variable, for the element that owns `<html>`. */
export const fontVariables = [
  sans.variable,
  sansExt.variable,
  sansDevanagari.variable,
  endonym.variable,
  serif.variable,
  serifExt.variable,
].join(" ");
