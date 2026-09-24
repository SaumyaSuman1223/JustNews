/**
 * The product's two typefaces, plus their Devanagari counterparts.
 *
 * `next/font` downloads and self-hosts these at build time and emits a
 * `size-adjust`ed local fallback, which is what keeps the swap from shifting
 * layout - the design system's "zero layout shift after first paint" is not
 * achievable with a `<link>` to fonts.googleapis.com.
 *
 * Four families sounds like a lot; it is two, twice. Cormorant Garamond and
 * IBM Plex Sans carry Latin, and neither contains a single Devanagari glyph -
 * a Hindi headline in Cormorant is tofu or a silent fallback to whatever the
 * OS picks, which is not a design decision. The Devanagari faces are declared
 * with `preload: false` so an English or Spanish page never pays for them;
 * they are fetched only when `:lang(hi)` actually resolves to them.
 */
import { Cormorant_Garamond, IBM_Plex_Sans } from "next/font/google";
import { IBM_Plex_Sans_Devanagari, Noto_Serif_Devanagari } from "next/font/google";

/** Display: headlines, mastheads, pull quotes. One display family, never two. */
export const display = Cormorant_Garamond({
  // Preloaded: Latin only, which covers English and Spanish. The latin-ext
  // faces are still declared, by unicode-range, and fetched only by a page
  // that uses one of their characters.
  subsets: ["latin"],
  // No `weight`: the variable font, one file per style that carries every
  // weight the design uses (400 to 700) - smaller than the four static
  // weights it replaces, twice over for the italic.
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-display-latin",
});

/** Interface: navigation, metadata, labels, controls. Variable, as above. */
export const ui = IBM_Plex_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-ui-latin",
});

/** Display, Devanagari. Variable weight, so headlines keep their hierarchy. */
export const displayDevanagari = Noto_Serif_Devanagari({
  subsets: ["devanagari"],
  display: "swap",
  preload: false,
  variable: "--font-display-deva",
});

/** Interface, Devanagari. Plex's own sibling, so the pairing holds in Hindi.
 * Static only, so two weights: 500 falls to 400, as the browser's matching
 * rules would pick anyway. */
export const uiDevanagari = IBM_Plex_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "600"],
  display: "swap",
  preload: false,
  variable: "--font-ui-deva",
});

/** Every font variable, for the element that owns `<html>`. */
export const fontVariables = [
  display.variable,
  ui.variable,
  displayDevanagari.variable,
  uiDevanagari.variable,
].join(" ");
