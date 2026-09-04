import type { CorpusStats } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * "Today at a glance" - real corpus counts, not invented reader numbers.
 *
 * The direction documents both ask for figures like "52K readers" as set
 * dressing; this product has no view-counting to back that, and CLAUDE.md's
 * data rules leave no room for a number that isn't a real query result. So
 * this shows what the corpus actually knows: how many articles, sources,
 * languages and story clusters are in today's window.
 */
export function GlanceRail({ stats, locale }: { stats: CorpusStats; locale: LocaleCode }) {
  const rows: [string, number][] = [
    [t(locale, "stats.articles"), stats.articles],
    [t(locale, "stats.sources"), stats.sources],
    [t(locale, "stats.languages"), stats.languages],
    [t(locale, "stats.stories"), stats.story_clusters],
  ];

  return (
    <section className="glance" aria-labelledby="glance-heading">
      <h2 id="glance-heading" className="glance__heading">
        {t(locale, "home.glance.heading")}
      </h2>
      <dl className="glance__list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dd>{value.toLocaleString(locale)}</dd>
            <dt>{label}</dt>
          </div>
        ))}
      </dl>
    </section>
  );
}
