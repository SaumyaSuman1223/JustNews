import Image from "next/image";
import Link from "next/link";

import type { Issue, IssuePageContent } from "@/lib/api";
import { datelineCity, t, type LocaleCode } from "@/lib/i18n";

/**
 * One page of The Aquila Tribune, rendered as a sheet of paper.
 *
 * The composition is the composer's, not this component's: `role` says
 * whether an article runs as the lead, a column, or a line in the brief, and
 * the layout follows. Nothing here re-ranks or re-orders - the issue was
 * frozen hours ago (ADR 0012) and this draws it.
 *
 * The paper is a warm surface with a stacked edge, not a photographic
 * texture. The direction document bans "overly realistic newspaper textures"
 * and "fake paper physics" in the same breath as it asks for a newspaper, and
 * the reference mockups do render a coffee cup - the written rule wins over
 * the rendered one, because the pastiche version of this reads as a novelty
 * and stops being readable at the second page.
 */
export function IssuePaper({
  issue,
  page,
  locale,
}: {
  issue: Issue;
  page: IssuePageContent;
  locale: LocaleCode;
}) {
  const lead = page.slots.find((slot) => slot.role === "lead");
  const secondaries = page.slots.filter((slot) => slot.role === "secondary");
  const briefs = page.slots.filter((slot) => slot.role === "brief");
  const isFront = page.page_no === 1;

  const published = new Date(issue.published_at);
  const dateLine = new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(published);
  // A newspaper's dateline names where the edition was filed. This product has
  // one worldwide edition per language, so for most locales there is no such
  // place, and inventing one would be a lie printed in the masthead. Absent a
  // real city, the line is just the date.
  const city = datelineCity(locale);
  // The hour is the edition's, not the composer's - see `edition_published_at`
  // in the composer. Printing it is what makes that guarantee checkable.
  const editionTime = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(published);
  const editionName = t(
    locale,
    `aquila.edition.${issue.edition_slot}` as "aquila.edition.morning",
  );

  return (
    <article className="paper" aria-label={t(locale, "aquila.pageLabel", { page: page.page_no })}>
      {isFront ? (
        // Coverage line, wordmark, strap. The coverage line is masthead
        // furniture, never navigation - nothing in it is clickable, and it
        // stays a single line of standing type (audit §6 bans a category
        // navbar in Aquila; §10 wants exactly these words in the header).
        <header className="paper__masthead">
          <p className="paper__standfirst">{t(locale, "aquila.standfirst")}</p>
          <h1 className="paper__title">{t(locale, "aquila.title")}</h1>
          <p className="paper__strap">{t(locale, "aquila.strap")}</p>
        </header>
      ) : (
        <header className="paper__sectionhead">
          <h2>{page.title}</h2>
          <span className="paper__folio">{page.page_no}</span>
        </header>
      )}

      <div className="paper__rule">
        <span>
          {editionName} · {t(locale, "aquila.volume", { volume: issue.volume, number: issue.number })}
        </span>
        <span>{city ? t(locale, "aquila.dateline", { city, date: dateLine }) : dateLine}</span>
        <span>{t(locale, "aquila.editionTime", { time: editionTime })}</span>
      </div>

      {page.slots.length === 0 ? (
        <p className="paper__empty">{t(locale, "aquila.pageEmpty")}</p>
      ) : (
        <div className="paper__body">
          {lead && (
            <section className="paper__lead">
              {lead.article.image_url && (
                // `unoptimized`, like every other image in the product: the
                // source is the publisher's own CDN and next/image would
                // need each of those hosts in remotePatterns.
                <Image
                  className="paper__lead-image"
                  src={lead.article.image_url}
                  alt=""
                  width={1200}
                  height={675}
                  sizes="(max-width: 46rem) 100vw, 40rem"
                  unoptimized
                  priority
                />
              )}
              <div className="paper__lead-text">
                <h2 className="paper__lead-headline">
                  <Link href={`/${locale}/a/${lead.article.id}`}>{lead.article.title}</Link>
                </h2>
                {lead.article.snippet && (
                  <p className="paper__deck">{lead.article.snippet}</p>
                )}
                <p className="paper__byline">{lead.article.source_name}</p>
              </div>
            </section>
          )}

          {secondaries.length > 0 && (
            <section className="paper__columns">
              {secondaries.map((slot) => (
                <div className="paper__column" key={slot.position}>
                  <h3 className="paper__column-headline">
                    <Link href={`/${locale}/a/${slot.article.id}`}>{slot.article.title}</Link>
                  </h3>
                  {slot.article.snippet && (
                    <p className="paper__column-deck">{slot.article.snippet}</p>
                  )}
                  <p className="paper__byline">{slot.article.source_name}</p>
                </div>
              ))}
            </section>
          )}

          {briefs.length > 0 && (
            <section className="paper__brief">
              <h2 className="paper__brief-heading">{t(locale, "aquila.brief")}</h2>
              <ol className="paper__brief-list">
                {briefs.map((slot, index) => (
                  <li key={slot.position}>
                    {/* The number is the running order the composer set, so
                        it is content rather than decoration - the design
                        system's rule that a structural device has to encode
                        something true. */}
                    <span className="paper__brief-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <Link href={`/${locale}/a/${slot.article.id}`}>{slot.article.title}</Link>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      )}

      <footer className="paper__footer">{t(locale, "aquila.footer")}</footer>
    </article>
  );
}
