import Link from "next/link";

import type { RelatedTopic, TopicOverview } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/** My Desk's topic-detail right rail: real counts, and topics that actually
 * co-occur with this one in the corpus - see the API's own note on why that
 * beats a taxonomy-sibling lookup while only level-1 topics are loaded. */
export function DeskRail({
  overview,
  related,
  locale,
}: {
  overview: TopicOverview | null;
  related: RelatedTopic[];
  locale: LocaleCode;
}) {
  return (
    <div className="desk-layout__rail">
      {overview && (
        <section className="glance" aria-labelledby="desk-overview-heading">
          <h2 id="desk-overview-heading" className="glance__heading">
            {t(locale, "desk.overview.heading")}
          </h2>
          <dl className="glance__list">
            <div>
              <dd>{overview.articles.toLocaleString(locale)}</dd>
              <dt>{t(locale, "stats.articles")}</dt>
            </div>
            <div>
              <dd>{overview.sources.toLocaleString(locale)}</dd>
              <dt>{t(locale, "stats.sources")}</dt>
            </div>
            <div>
              <dd>{overview.stories.toLocaleString(locale)}</dd>
              <dt>{t(locale, "stats.stories")}</dt>
            </div>
          </dl>
        </section>
      )}

      {related.length > 0 && (
        <section className="trending trending--rail" aria-labelledby="desk-related-heading">
          <h2 id="desk-related-heading" className="trending__heading">
            {t(locale, "desk.related.heading")}
          </h2>
          <ul className="related-topics">
            {related.map((topic) => (
              <li key={topic.id}>
                <Link href={`/${locale}/desk/${encodeURIComponent(topic.id)}`}>{topic.label}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
