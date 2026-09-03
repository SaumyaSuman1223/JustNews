import { ImageResponse } from "next/og";

/**
 * The "JN" monogram behind every generated app icon - the same "Just" /
 * "News" split as the masthead wordmark (globals.css), just without room for
 * the full word at icon sizes. No custom font is loaded here (the edge
 * image-generation runtime doesn't have the site's self-hosted display
 * serif available without embedding it), so this falls back to a generic
 * serif stack - a deliberate, visible trade-off rather than a silent one.
 *
 * `maskable` shrinks the mark so it survives an OS's circular/rounded-square
 * icon mask without clipping - the standard maskable-icon safe-zone practice
 * (content kept inside the inner ~80% of the canvas).
 */
export function monogramIcon(size: number, { maskable = false }: { maskable?: boolean } = {}) {
  const scale = maskable ? 0.42 : 0.56;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
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
            fontSize: size * scale,
            lineHeight: 1,
            letterSpacing: "-0.02em",
            // The fallback serif's reserved descender space outweighs "J"'s
            // actual descender, so flex-centering the line box (not the
            // glyph ink) sits visibly low. Nudged up empirically, measured
            // against the rendered pixel bounding box rather than guessed.
            // Only this inner wrapper moves - the outer div keeps the
            // background pinned to the full canvas.
            transform: "translateY(-13%)",
          }}
        >
          <span style={{ color: "#121614" }}>J</span>
          <span style={{ color: "#0f6b53" }}>N</span>
        </div>
      </div>
    ),
    { width: size, height: size },
  );
}
