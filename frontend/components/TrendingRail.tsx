import Link from "next/link";

import type { Article } from "@/lib/api";
import { type LocaleCode, formatRelativeTime, t } from "@/lib/i18n";

/**
 * What readers are clicking, most-clicked first.
 *
 * Ranked on behaviour rather than recency, which is the only reason it earns
 * space beside a feed that is already recency-ordered - a rail repeating the
 * feed's own ordering would be decoration. Numbered because the order is the
 * information here.
 */
export function TrendingRail({
  articles,
  locale,
  variant = "panel",
}: {
  articles: Article[];
  locale: LocaleCode;
  /** "rail" drops the panel's own margins - the rail column supplies the
   * gap between modules instead, so a nested margin would double it. */
  variant?: "panel" | "rail";
}) {
  if (articles.length === 0) return null;

  return (
    <section
      className={`trending${variant === "rail" ? " trending--rail" : ""}`}
      aria-labelledby="trending-heading"
    >
      <h2 id="trending-heading" className="trending__heading">
        {t(locale, "trending.heading")}
      </h2>
      <ol className="trending__list">
        {articles.map((article) => (
          <li key={article.id} className="trending__item">
            <Link className="trending__link" href={`/${locale}/a/${article.id}`}>
              <span lang={article.language}>{article.title}</span>
            </Link>
            <p className="trending__meta">
              {article.source_name} · {formatRelativeTime(article.published_at, locale)}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
