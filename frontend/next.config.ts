import type { NextConfig } from "next";

/**
 * What a page may load. Images are hot-linked from every publisher, so
 * `img-src` is any HTTPS host; everything else is this origin, plus Supabase
 * for the browser's auth calls. Scripts allow inline because Next streams
 * its payload as inline scripts and this app does not thread a nonce through
 * them - what the policy still rules out is script from any other host,
 * plugins, framing, and forms posting elsewhere.
 *
 * Production only: development needs `eval` for Fast Refresh.
 */
function contentSecurityPolicy(): string {
  const supabase = process.env.NEXT_PUBLIC_SUPABASE_URL
    ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).origin
    : "";
  const supabaseSocket = supabase.replace(/^http/, "ws");
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' https: data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${supabase} ${supabaseSocket}`.trim(),
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");
}

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  // Two years, as HSTS preload expects. Ignored over plain HTTP, so local
  // `next start` is unaffected.
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  // Location only for the weather widget's "use my location", on this
  // origin; nothing else the browser offers is used.
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(self), payment=(), usb=(), browsing-topics=()",
  },
  ...(process.env.NODE_ENV === "production"
    ? [{ key: "Content-Security-Policy", value: contentSecurityPolicy() }]
    : []),
];

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
        headers: securityHeaders,
      },
    ];
  },
};

export default config;
