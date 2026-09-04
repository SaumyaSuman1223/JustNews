import Link from "next/link";

import type { Article } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * The Brief: a short, real list of today's top stories, linking out to the
 * full publication.
 *
 * Not an AI summary - there is no summarizer in this product, and a "brief"
 * that read like one would claim a capability that doesn't exist. This is
 * exactly what it looks like: a list, headlines only, and a link to the
 * issue those stories belong to.
 */
export function DailyBrief({
  articles,
  locale,
}: {
  articles: Article[];
  locale: LocaleCode;
}) {
  if (articles.length === 0) return null;

  return (
    <section className="brief" aria-labelledby="brief-heading">
      <h2 id="brief-heading" className="brief__heading">
        {t(locale, "home.brief.heading")}
      </h2>
      <ul className="brief__list">
        {articles.map((article) => (
          <li key={article.id}>
            <Link href={`/${locale}/a/${article.id}`}>{article.title}</Link>
          </li>
        ))}
      </ul>
      <Link className="brief__cta" href={`/${locale}/aquila`}>
        {t(locale, "home.brief.cta")}
      </Link>
    </section>
  );
}
