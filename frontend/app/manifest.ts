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
    background_color: "#f7f8f7",
    theme_color: "#0f6b53",
    icons: [
      { src: "/icon-192", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512-maskable", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
