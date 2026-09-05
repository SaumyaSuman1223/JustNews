import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";

// Without this, every relative URL a nested layout/page hands to the
// metadata API (alternates.canonical, alternates.languages, openGraph
// images) is left relative instead of being resolved against it - which is
// exactly what a canonical tag and hreflang alternates are not allowed to
// be. Same env var sitemap.ts/robots.ts already use for the same reason.
export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
};

export const viewport: Viewport = {
  // Matches globals.css's --ground in each theme (#f5f1e8 light, #1a1b19
  // dark) - the browser chrome/status bar should read as this product's
  // own paper or ink, not the old cool green.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f1e8" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1b19" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <ServiceWorkerRegistration />
      {children}
    </>
  );
}
