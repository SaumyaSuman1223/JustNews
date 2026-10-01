import { ImageResponse } from "next/og";

import { BRAND, brandFont, brandTextFont } from "@/lib/icon";

// The default share image for Discover and any page that does not set its
// own (article and story pages use the publisher's photo instead - see
// their generateMetadata). The wordmark as the sidebar sets it - Anek
// condensed, "News" in the brand pink - over a short pink rule, with the
// English tagline: the one subset the embedded fonts carry (lib/icon.tsx).
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
        justifyContent: "center",
        padding: "0 96px",
        background: BRAND.porcelain,
      }}
    >
      <div
        style={{
          display: "flex",
          fontFamily: "Anek Condensed",
          fontWeight: 800,
          fontSize: 200,
          lineHeight: 1,
        }}
      >
        <span style={{ color: BRAND.ink }}>Just</span>
        <span style={{ color: BRAND.pink }}>News</span>
      </div>
      <div
        style={{ display: "flex", width: 168, height: 12, marginTop: 28, background: BRAND.pink }}
      />
      <div
        style={{
          display: "flex",
          marginTop: 36,
          fontFamily: "Anek",
          fontSize: 48,
          lineHeight: 1.2,
          color: BRAND.ink,
        }}
      >
        The same story, in every language it is reported in.
      </div>
    </div>,
    {
      ...size,
      fonts: [
        { name: "Anek Condensed", data: await brandFont(), weight: 800 },
        { name: "Anek", data: await brandTextFont(), weight: 400 },
      ],
    },
  );
}
