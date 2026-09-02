import { ImageResponse } from "next/og";

// The default OG image for the home feed and any nested route that doesn't
// set its own `openGraph.images` (article and story pages override this
// with the real publisher photo instead - see their generateMetadata).
// English-only, matching manifest.ts's tagline - full per-locale OG copy is
// a larger i18n gap than this one image solves.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#f7f8f7",
        }}
      >
        <div
          style={{
            display: "flex",
            fontFamily: "serif",
            fontWeight: 700,
            fontSize: 120,
            lineHeight: 1,
            letterSpacing: "-0.02em",
          }}
        >
          <span style={{ color: "#121614" }}>Just</span>
          <span style={{ color: "#0f6b53" }}>News</span>
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 28,
            fontFamily: "sans-serif",
            fontSize: 32,
            color: "#66746f",
          }}
        >
          Personalised, multilingual news.
        </div>
      </div>
    ),
    { ...size },
  );
}
