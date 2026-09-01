import type { MetadataRoute } from "next";

import { locales } from "@/lib/i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Never indexable: an internal ops tool, not a page for the public.
        disallow: ["/admin"],
      },
    ],
    // One sitemap per locale (app/sitemap.ts's generateSitemaps) - Next does
    // not synthesise a combining /sitemap.xml index for a multi-sitemap
    // setup, so every one of them is listed here instead.
    sitemap: locales.map((_, id) => `${SITE_URL}/sitemap/${id}.xml`),
  };
}
