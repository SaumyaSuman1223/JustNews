import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    // The client router keeps a page it has shown for 30s (dynamic) or 5
    // minutes (static), so Back, and switching between tabs already visited,
    // are instant instead of a fresh server round trip each time. Next 15's
    // default for dynamic pages is 0 - every navigation refetched
    // (docs/decisions/0014).
    staleTimes: { dynamic: 30, static: 300 },
  },
  images: {
    // Publisher images are hot-linked from wherever the source hosts them, so
    // the allow-list has to be open. Sizes are constrained instead, and every
    // card reserves its space through a fixed aspect ratio.
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default config;
