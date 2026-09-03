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
  themeColor: "#0f6b53",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <ServiceWorkerRegistration />
      {children}
    </>
  );
}
