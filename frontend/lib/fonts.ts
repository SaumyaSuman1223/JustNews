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
  subsets: ["latin", "latin-ext"],
  // 600 is the headline weight; 400/500 carry decks and pull quotes. Cormorant
  // is a light-bodied face, so its "bold" reads closer to a normal serif's
  // semibold - hence 700 for the front-page lead rather than 600.
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-display-latin",
});

/** Interface: navigation, metadata, labels, controls. */
export const ui = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-ui-latin",
});

/** Display, Devanagari. Variable weight, so headlines keep their hierarchy. */
export const displayDevanagari = Noto_Serif_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  preload: false,
  variable: "--font-display-deva",
});

/** Interface, Devanagari. Plex's own sibling, so the pairing holds in Hindi. */
export const uiDevanagari = IBM_Plex_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600"],
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
