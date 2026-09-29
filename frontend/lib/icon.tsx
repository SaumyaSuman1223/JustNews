import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

/**
 * The brand's own face and colours, for every image the site generates: the
 * app icons, the favicon and the share card. They were a generic serif in
 * the green of an earlier identity; these are the masthead's - Cormorant
 * Garamond on warm paper, "News" in brass.
 *
 * The font is a Latin subset of Cormorant Garamond SemiBold (SIL OFL, see
 * assets/fonts/OFL-CormorantGaramond.txt), small enough to read on every request. It covers
 * the wordmark and the English tagline; nothing else is drawn in it.
 */
export const BRAND = {
  paper: "#f5f1e8",
  ink: "#171717",
  brass: "#7a6444",
  muted: "#6b675f",
};

let font: Promise<Buffer> | null = null;

export function brandFont(): Promise<Buffer> {
  font ??= readFile(join(process.cwd(), "assets/fonts/CormorantGaramond-600-latin.ttf"));
  return font;
}

/**
 * The "JN" monogram behind every app icon and the favicon. `maskable` keeps
 * the mark inside the inner 80% an OS may crop to a circle or squircle.
 */
export async function monogramIcon(
  size: number,
  { maskable = false }: { maskable?: boolean } = {},
) {
  const scale = maskable ? 0.46 : 0.62;
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: BRAND.paper,
      }}
    >
      <div
        style={{
          display: "flex",
          fontFamily: "Cormorant Garamond",
          fontWeight: 600,
          fontSize: size * scale,
          lineHeight: 1,
          letterSpacing: "-0.03em",
          // Centre the ink rather than the line box: Cormorant's line box
          // carries more space below the baseline than "J" uses.
          transform: "translateY(-6%)",
        }}
      >
        <span style={{ color: BRAND.ink }}>J</span>
        <span style={{ color: BRAND.brass }}>N</span>
      </div>
    </div>,
    {
      width: size,
      height: size,
      fonts: [{ name: "Cormorant Garamond", data: await brandFont(), weight: 600 }],
    },
  );
}
