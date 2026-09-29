/**
 * The product's two typefaces, plus their Devanagari counterparts, served
 * from files in this repository (assets/fonts/web).
 *
 * They were fetched from Google Fonts at build time, and a build failed the
 * day Google answered unexpectedly. These are the same files - Google's own
 * subsets, by unicode-range - so pages download exactly what they did.
 * Licences: all four families are SIL Open Font License 1.1 (see
 * assets/fonts/README.md).
 *
 * Each script's subset is its own family, so a page fetches only the ranges
 * its text uses: an English page never downloads the Devanagari files, and
 * the extended-Latin file arrives only for a name like "Erdoğan". The
 * metric-matched fallback that keeps the swap from shifting layout sits on
 * the second family in each stack (the first carries none), so it comes
 * after the basic-Latin face and before any other script's.
 *
 * The unicode-ranges are written out in each call because next/font takes
 * only literal values; they are Google's own ranges for each subset.
 */
import localFont from "next/font/local";

const LATIN =
  "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD";
const LATIN_EXT =
  "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF";
const DEVANAGARI =
  "U+0900-097F, U+1CD0-1CF9, U+200C-200D, U+20A8, U+20B9, U+20F0, U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B09";

/** Display: headlines, mastheads, pull quotes. Variable, 300-700, with its
 * italic. Basic Latin, preloaded - English and Spanish are set in it. */
export const display = localFont({
  src: [
    {
      path: "../assets/fonts/web/cormorant-latin-normal-300-700.woff2",
      weight: "300 700",
      style: "normal",
    },
    {
      path: "../assets/fonts/web/cormorant-latin-italic-300-700.woff2",
      weight: "300 700",
      style: "italic",
    },
  ],
  display: "swap",
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
    },
  ],
  adjustFontFallback: false,
  variable: "--font-display-latin",
});

export const displayExt = localFont({
  src: [
    {
      path: "../assets/fonts/web/cormorant-latin-ext-normal-300-700.woff2",
      weight: "300 700",
      style: "normal",
    },
    {
      path: "../assets/fonts/web/cormorant-latin-ext-italic-300-700.woff2",
      weight: "300 700",
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
  variable: "--font-display-latin-ext",
});

/** Interface: navigation, metadata, labels, controls. Variable, 100-700. */
export const ui = localFont({
  src: [
    {
      path: "../assets/fonts/web/plex-latin-normal-100-700.woff2",
      weight: "100 700",
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
  ],
  adjustFontFallback: false,
  variable: "--font-ui-latin",
});

export const uiExt = localFont({
  src: [
    {
      path: "../assets/fonts/web/plex-latin-ext-normal-100-700.woff2",
      weight: "100 700",
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
  ],
  adjustFontFallback: "Arial",
  variable: "--font-ui-latin-ext",
});

/** Display, Devanagari. Variable weight, so headlines keep their hierarchy. */
export const displayDevanagari = localFont({
  src: [
    {
      path: "../assets/fonts/web/noto-serif-deva-devanagari-normal-100-900.woff2",
      weight: "100 900",
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
  adjustFontFallback: "Times New Roman",
  variable: "--font-display-deva",
});

/** Interface, Devanagari. Plex's own sibling, so the pairing holds in Hindi.
 * Static only, so two weights: 500 falls to 400, as the browser's matching
 * rules would pick anyway. */
export const uiDevanagari = localFont({
  src: [
    {
      path: "../assets/fonts/web/plex-deva-devanagari-normal-400.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../assets/fonts/web/plex-deva-devanagari-normal-600.woff2",
      weight: "600",
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
  variable: "--font-ui-deva",
});

/** Every font variable, for the element that owns `<html>`. */
export const fontVariables = [
  display.variable,
  displayExt.variable,
  ui.variable,
  uiExt.variable,
  displayDevanagari.variable,
  uiDevanagari.variable,
].join(" ");
