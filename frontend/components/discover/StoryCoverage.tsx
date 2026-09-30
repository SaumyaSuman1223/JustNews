"use client";

import { OutletIcon, originOf } from "@/components/discover/OutletIcon";
import type { Article } from "@/lib/api";
import { formatRelativeTime, t, tPlural, type LocaleCode } from "@/lib/i18n";
import { reportClick as sendClick } from "@/lib/track";

export interface CoverageColumn {
  language: string;
  /** The language's own name, "हिन्दी" - this is a heading, not a sentence. */
  label: string;
  htmlLang: string;
  articles: Article[];
}

/**
 * A story's coverage laid out to compare: one column per language, each
 * report a row - the outlet, its headline, when it ran - opening at the
 * publisher. No photos: five pictures of the same rocket say nothing a
 * reader comparing coverage needs, and the outlet's name says everything.
 *
 * Each column is an anchor (#coverage-{language}) the story header's
 * language chips jump to.
 */
export function StoryCoverage({
  locale,
  columns,
  headingLevel = 2,
}: {
  locale: LocaleCode;
  columns: CoverageColumn[];
  headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 3 ? "h3" : "h2";
  let position = 0;

  function reportClick(article: Article, at: number) {
    // Also how a signed-out reader's device remembers the read (ADR 0015).
    sendClick({ articleId: article.id, surface: "topic", position: at, locale });
  }

  return (
    <div className="coverage-columns">
      {columns.map((column) => (
        <section
          key={column.language}
          id={`coverage-${column.language}`}
          className="coverage-column"
          aria-labelledby={`coverage-${column.language}-heading`}
        >
          <Heading className="coverage-column__heading" id={`coverage-${column.language}-heading`}>
            <span lang={column.htmlLang}>{column.label}</span>
            <span className="coverage-column__count">
              {tPlural(locale, "story.reports", column.articles.length)}
            </span>
          </Heading>
          <ol className="coverage-rows">
            {column.articles.map((article) => {
              const at = position++;
              return (
                <li key={article.id} className="coverage-row">
                  <a
                    className="coverage-row__link"
                    href={article.url}
                    onClick={() => reportClick(article, at)}
                  >
                    <span className="coverage-row__outlet">
                      <OutletIcon name={article.source_name} homepage={originOf(article.url)} />
                      {article.source_name}
                    </span>
                    <span className="coverage-row__title" lang={column.htmlLang}>
                      {article.title}
                    </span>
                  </a>
                  <time
                    className="coverage-row__time"
                    dateTime={article.published_at}
                    suppressHydrationWarning
                  >
                    {formatRelativeTime(article.published_at, locale)}
                  </time>
                </li>
              );
            })}
          </ol>
        </section>
      ))}
      <p className="visually-hidden">{t(locale, "story.coverage.opensAtPublisher")}</p>
    </div>
  );
}
