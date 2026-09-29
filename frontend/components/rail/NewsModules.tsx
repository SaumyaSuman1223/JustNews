import Link from "next/link";

import type { AcrossLanguages, Article, Issue, IssuePageContent } from "@/lib/api";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import {
  languageName as displayLanguage,
  locales,
  t,
  tPlural,
  type LocaleCode,
  type MessageKey,
} from "@/lib/i18n";

/** A language's own name, in its own script: "हिन्दी", not "Hindi". */
function languageName(code: string): { label: string; lang: string } {
  const known = locales.find((locale) => locale.code === code);
  return { label: known?.label ?? code.toUpperCase(), lang: known?.htmlLang ?? code };
}

/**
 * The same story, in each language the reader reads, with how many outlets
 * in every language are reporting it. This is the product's clustering made
 * visible: headlines quoted only in the reader's languages, the others named
 * and counted.
 */
export function AcrossLanguagesModule({
  locale,
  stories,
}: {
  locale: LocaleCode;
  stories: AcrossLanguages[];
}) {
  return (
    <>
      <p className="rail-widget__sub">{t(locale, "across.subtitle")}</p>
      <ol className="across">
        {stories.map((item) => {
          // The interface language's headline leads when there is one.
          const ordered = [...item.headlines].sort(
            (a, b) => Number(b.language === locale) - Number(a.language === locale),
          );
          const [first, ...rest] = ordered;
          if (!first) return null;
          return (
            <li key={item.story.id} className="across__story">
              <Link
                className="across__headline"
                href={`/${locale}/story/${item.story.id}`}
                lang={languageName(first.language).lang}
              >
                {first.title}
              </Link>
              {rest.map((headline) => (
                <p
                  key={headline.language}
                  className="across__alt"
                  lang={languageName(headline.language).lang}
                >
                  {headline.title}
                </p>
              ))}
              <p className="across__coverage">
                <span className="visually-hidden">{t(locale, "across.outlets")} </span>
                {item.coverage.map((entry, index) => {
                  return (
                    <span key={entry.language} className="across__lang">
                      {index > 0 && <span aria-hidden="true"> · </span>}
                      {displayLanguage(entry.language, locale, { capitalize: true })}{" "}
                      <b className="across__count">{entry.source_count.toLocaleString(locale)}</b>
                    </span>
                  );
                })}
              </p>
            </li>
          );
        })}
      </ol>
    </>
  );
}

const EDITION_KEYS: Record<string, MessageKey> = {
  morning: "aquila.edition.morning",
  midday: "aquila.edition.midday",
  evening: "aquila.edition.evening",
};

/**
 * Today's edition of the Aquila Tribune, as a teaser: its lead story, which
 * edition it is, and what sections it carries. Aquila is the part of the
 * product nobody else has; this puts it on the front door.
 */
export function TodaysAquilaModule({
  locale,
  issue,
  front,
}: {
  locale: LocaleCode;
  issue: Issue;
  front: IssuePageContent | null;
}) {
  const lead = front?.slots.find((slot) => slot.role === "lead")?.article;
  // The sections by the names the rest of the product uses ("Conflict", not
  // "Conflict, war and peace").
  const sections = issue.sections
    .slice(1, 4)
    .map((section) =>
      section.topic_id
        ? curatedTopicLabel(section.topic_id, section.title ?? "", locale)
        : (section.title ?? ""),
    )
    .filter(Boolean);
  const edition = t(locale, EDITION_KEYS[issue.edition_slot] ?? "aquila.edition.morning");
  return (
    <Link className="aquila-teaser" href={`/${locale}/aquila`}>
      <span className="aquila-teaser__masthead">{t(locale, "aquila.title")}</span>
      <span className="aquila-teaser__edition">
        {edition} · {tPlural(locale, "aquila.pageCount", issue.page_count)}
      </span>
      {lead && (
        <span className="aquila-teaser__lead" lang={languageName(lead.language).lang}>
          {lead.title}
        </span>
      )}
      {sections.length > 0 && (
        <span className="aquila-teaser__sections">{sections.join(" · ")}</span>
      )}
      <span className="aquila-teaser__open">{t(locale, "aquila.open")}</span>
    </Link>
  );
}

/** What readers are opening today, most-opened first: behaviour, not the
 * feed's own order restated. The rank is real, so it is numbered. */
export function MostReadModule({ locale, articles }: { locale: LocaleCode; articles: Article[] }) {
  return (
    <ol className="most-read">
      {articles.map((article) => (
        <li key={article.id}>
          <Link
            className="most-read__title"
            href={`/${locale}/a/${article.id}`}
            lang={languageName(article.language).lang}
          >
            {article.title}
          </Link>
          <span className="most-read__source">{article.source_name}</span>
        </li>
      ))}
    </ol>
  );
}
