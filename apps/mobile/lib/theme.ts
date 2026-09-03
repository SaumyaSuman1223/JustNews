/**
 * Design tokens, read directly from frontend/app/globals.css's `:root` block
 * so the two apps read as one product rather than two designs that happen to
 * share a backend. Not a literal port - RN has no CSS - just the same values.
 *
 * Light only this slice; dark-mode parity is deferred (frontend/globals.css's
 * `@media (prefers-color-scheme: dark)` block has the values whenever it's
 * picked up).
 */
export const colors = {
  ground: "#f7f8f7",
  surface: "#ffffff",
  surfaceSub: "#eef1ef",
  text: "#121614",
  textMid: "#3d4744",
  textMuted: "#66746f",
  border: "#dde3e0",
  accent: "#0f6b53",
  accentSoft: "#dcebe5",
  danger: "#96382c",
} as const;

/** The 4pt/8pt rhythm from docs/design/design-system.md, as RN's unitless dp. */
export const space = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  6: 24,
  8: 32,
  12: 48,
} as const;

/**
 * frontend's --type-lead/section/card/list/body/meta rem steps, converted to
 * dp (1rem ≈ 16dp). Lead is fixed here rather than the web's fluid clamp()
 * - RN has no viewport-relative unit, and a phone's width band is narrow
 * enough that a fixed size is the honest equivalent.
 */
export const type = {
  lead: 26,
  section: 20,
  card: 17,
  list: 16,
  body: 15,
  meta: 12,
} as const;

export const radius = 8;

/**
 * RN's `fontFamily` needs the exact family name a loaded font registers
 * under - set once fonts load (see app/_layout.tsx's useFonts). Falls back to
 * the platform default while loading or if a font fails, rather than a
 * blank screen.
 */
export const fonts = {
  display: "PlayfairDisplay_600SemiBold",
  displayBold: "PlayfairDisplay_700Bold",
} as const;
