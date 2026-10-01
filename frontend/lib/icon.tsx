import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

/**
 * The brand's own face and colours, for every image the site generates: the
 * app icons, the favicon and the share card (ADR 0017) - Anek set condensed,
 * ink and porcelain, "News" in the brand pink.
 *
 * Two static instances of Anek Latin, basic-Latin subset only (SIL OFL, see
 * assets/fonts/OFL-AnekLatin.txt), small enough to read on every request:
 * the condensed heavy cut for the wordmark and the monogram, the regular
 * cut for the share card's tagline. The image renderer reads TrueType, not
 * the variable WOFF2 the pages use, which is why these are separate files.
 */
export const BRAND = {
  porcelain: "#f3f3f5",
  ink: "#12131c",
  /* The brand pink: the light theme's --mark for the share card, and the
     dark theme's for the monogram, which sits on ink. */
  pink: "#e5196f",
  pinkOnInk: "#ff4f98",
  muted: "#5c5f72",
};

let display: Promise<Buffer> | null = null;
let text: Promise<Buffer> | null = null;

export function brandFont(): Promise<Buffer> {
  display ??= readFile(join(process.cwd(), "assets/fonts/AnekLatin-Condensed-800-latin.ttf"));
  return display;
}

export function brandTextFont(): Promise<Buffer> {
  text ??= readFile(join(process.cwd(), "assets/fonts/AnekLatin-400-latin.ttf"));
  return text;
}

/**
 * The "JN" monogram behind every app icon and the favicon: porcelain "J",
 * pink "N", on ink - the wordmark's two colours, on the ground Aquila reads
 * on. `maskable` keeps the mark inside the inner 80% an OS may crop to a
 * circle or squircle.
 */
export async function monogramIcon(
  size: number,
  { maskable = false }: { maskable?: boolean } = {},
) {
  const scale = maskable ? 0.5 : 0.7;
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: BRAND.ink,
      }}
    >
      <div
        style={{
          display: "flex",
          fontFamily: "Anek Condensed",
          fontWeight: 800,
          fontSize: size * scale,
          lineHeight: 1,
          letterSpacing: "-0.01em",
          // Centre the ink rather than the line box: Anek's line box carries
          // more space below the baseline than "J" and "N" use.
          transform: "translateY(4%)",
        }}
      >
        <span style={{ color: BRAND.porcelain }}>J</span>
        <span style={{ color: BRAND.pinkOnInk }}>N</span>
      </div>
    </div>,
    {
      width: size,
      height: size,
      fonts: [{ name: "Anek Condensed", data: await brandFont(), weight: 800 }],
    },
  );
}
