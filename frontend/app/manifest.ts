import type { MetadataRoute } from "next";

// `/en`, not `/`: `/` is a server-side redirect through middleware.ts, which
// needs a live request to resolve - launching from the home-screen icon
// while offline would fail before the app ever loaded. A manifest's
// start_url is a fixed string regardless (it can't negotiate a visitor's
// locale), so the default locale is the only choice that also works offline.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "JustNews",
    short_name: "JustNews",
    description: "Personalised, multilingual news.",
    start_url: "/en",
    scope: "/",
    display: "standalone",
    // Matches the warm-paper token set in globals.css (--ground, --accent) -
    // an installed app's splash screen and status bar should not be the old
    // cool green this product no longer uses anywhere else.
    background_color: "#f5f1e8",
    theme_color: "#7a6444",
    icons: [
      { src: "/icon-192", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512-maskable", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
