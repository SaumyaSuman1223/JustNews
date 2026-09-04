import type { MetadataRoute } from "next";

import { getArticles } from "@/lib/api";
import { locales } from "@/lib/i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/** One sitemap per locale - the id Next passes to `sitemap()` below is an
 * index into `locales`, and Next assembles the `/sitemap.xml` index itself. */
export function generateSitemaps() {
  return locales.map((_, id) => ({ id }));
}

export default async function sitemap({ id }: { id: number }): Promise<MetadataRoute.Sitemap> {
  const locale = locales[id];
  if (!locale) return [];

  const articles = await getArticles({ languages: locale.code, pageSize: 50 });

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/${locale.code}`, changeFrequency: "always" as const, priority: 1 },
    // The three destinations (ADR 0011). Aquila outranks My Desk here because
    // it is the same publication for every reader in a locale and therefore
    // the one worth indexing; My Desk is personal and mostly signed-in.
    { url: `${SITE_URL}/${locale.code}/aquila`, changeFrequency: "daily" as const, priority: 0.8 },
    { url: `${SITE_URL}/${locale.code}/desk`, changeFrequency: "daily" as const, priority: 0.5 },
  ];

  const articleRoutes: MetadataRoute.Sitemap = articles.data.items.map((article) => ({
    url: `${SITE_URL}/${locale.code}/a/${article.id}`,
    lastModified: article.published_at,
    changeFrequency: "hourly" as const,
    priority: 0.7,
  }));

  return [...staticRoutes, ...articleRoutes];
}
