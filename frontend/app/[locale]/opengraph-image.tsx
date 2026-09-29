import { ImageResponse } from "next/og";

import { BRAND, brandFont } from "@/lib/icon";

// The default share image for Discover and any page that does not set its
// own (article and story pages use the publisher's photo instead - see
// their generateMetadata). The wordmark as the masthead sets it, on paper,
// under a double rule, with the English tagline - the one subset the
// embedded font carries (lib/icon.tsx).
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "JustNews";

export default async function Image() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: BRAND.paper,
        fontFamily: "Cormorant Garamond",
      }}
    >
      <div
        style={{
          display: "flex",
          fontWeight: 600,
          fontSize: 150,
          lineHeight: 1,
          letterSpacing: "-0.02em",
          paddingBottom: 26,
        }}
      >
        <span style={{ color: BRAND.ink }}>Just</span>
        <span style={{ color: BRAND.brass }}>News</span>
      </div>
      {/* The masthead's double rule, drawn as two lines: the image renderer
          has no `double` border style. */}
      <div style={{ display: "flex", width: 720, height: 4, background: BRAND.ink }} />
      <div
        style={{ display: "flex", width: 720, height: 1.5, marginTop: 4, background: BRAND.ink }}
      />
      <div style={{ display: "flex", marginTop: 30, fontSize: 44, color: BRAND.muted }}>
        The same story, in every language it is reported in.
      </div>
    </div>,
    {
      ...size,
      fonts: [{ name: "Cormorant Garamond", data: await brandFont(), weight: 600 }],
    },
  );
}
