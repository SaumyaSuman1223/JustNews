import { notFound } from "next/navigation";

import { getArticles } from "@/lib/api";
import { escapeXml } from "@/lib/feed";
import { isLocaleCode, locales } from "@/lib/i18n";

export const revalidate = 300;

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale: locale.code }));
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ locale: string }> },
) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();

  const articles = await getArticles({ languages: locale, pageSize: 50 });

  // Never full article text (CLAUDE.md): title, the same ≤300-char snippet
  // every card shows, and a link out to the publisher - not a substitute for
  // reading the source.
  const items = articles.data.items
    .map(
      (article) => `
    <item>
      <title>${escapeXml(article.title)}</title>
      <link>${escapeXml(article.url)}</link>
      <guid isPermaLink="false">justnews:article:${article.id}</guid>
      <pubDate>${new Date(article.published_at).toUTCString()}</pubDate>
      <source url="${escapeXml(article.url)}">${escapeXml(article.source_name)}</source>${
        article.snippet ? `\n      <description>${escapeXml(article.snippet)}</description>` : ""
      }
    </item>`,
    )
    .join("");

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>JustNews (${locale})</title>
    <link>${SITE_URL}/${locale}</link>
    <description>Personalised, multilingual news - headlines and links out to the publisher.</description>
    <language>${locale}</language>${items}
  </channel>
</rss>`;

  return new Response(body, {
    headers: { "content-type": "application/rss+xml; charset=utf-8" },
  });
}
