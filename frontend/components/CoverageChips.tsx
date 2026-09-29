import type { LanguageCoverage } from "@/lib/api";
import { type LocaleCode, locales, t } from "@/lib/i18n";

/**
 * The language split of one story: "English 1 · Español 3 · हिन्दी 2".
 *
 * This is the visual signature of the thing that makes this product
 * different. Ground News splits coverage by political leaning; this splits it
 * by language, which is only possible because the dedup layer clusters across
 * languages - the same event in three languages is one story here, not three
 * (ADR 0005).
 */
export function CoverageChips({
  coverage,
  locale,
  linkTo,
}: {
  coverage: LanguageCoverage[];
  locale: LocaleCode;
  /** Where each language's chip leads - the story page's own columns. A
   * chip that looks like a control and does nothing is worse than none. */
  linkTo?: (language: string) => string;
}) {
  if (coverage.length === 0) return null;

  return (
    <ul className="chip-list" aria-label={t(locale, "coverage.label")}>
      {coverage.map((entry) => {
        const known = locales.find((option) => option.code === entry.language);
        return (
          <li key={entry.language}>
            {/* A language we do not ship can still appear here: the corpus
                outlives a change to the launch set, and hiding it would
                misreport the coverage. */}
            {linkTo ? (
              <a className="chip chip--link" href={linkTo(entry.language)}>
                <span lang={known?.htmlLang ?? entry.language}>
                  {known?.label ?? entry.language}
                </span>
                <b className="chip__count">{entry.article_count.toLocaleString(locale)}</b>
              </a>
            ) : (
              <span className="chip">
                <span lang={known?.htmlLang ?? entry.language}>
                  {known?.label ?? entry.language}
                </span>
                <b className="chip__count">{entry.article_count.toLocaleString(locale)}</b>
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
