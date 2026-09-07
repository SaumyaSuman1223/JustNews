import Link from "next/link";

import { HalftoneImage } from "@/components/Halftone";
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
  onGoTo,
}: {
  issue: Issue;
  page: IssuePageContent;
  locale: LocaleCode;
  /** Jumps the reader to another page without a navigation - the same
   * client-side page change the contents panel uses. Undefined outside a
   * reading session (there is none today, but nothing here should require
   * one): a page reference then renders as plain text rather than a control
   * with nothing to do. */
  onGoTo?: (page: number) => void;
}) {
  const lead = page.slots.find((slot) => slot.role === "lead");
  const focus = page.slots.find((slot) => slot.role === "focus");
  const secondaries = page.slots.filter((slot) => slot.role === "secondary");
  const briefs = page.slots.filter((slot) => slot.role === "brief");
  const isFront = page.page_no === 1;
  // Audit §8: the right rail and a lower row of major stories are the same
  // pool of secondaries, split by position - first refusal on the rail,
  // which is also the picture-led one (see the composer's `prefer_image`
  // ordering), the rest into the lower row as text.
  const rail = secondaries.slice(0, 3);
  const lower = secondaries.slice(3, 6);

  const sectionTitle = (pageRef: number | null | undefined): string | null =>
    pageRef == null
      ? null
      : (issue.sections.find((section) => section.page_no === pageRef)?.title ?? null);

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
    <article
      className="paper"
      aria-label={t(locale, "aquila.pageLabel", { page: page.page_no })}
    >
      {isFront ? (
        // Three columns on a full-width sheet, stacked on a narrow one:
        // edition identity, wordmark, what the paper covers. The coverage
        // line is masthead furniture, never navigation - nothing in it is
        // clickable, and it stays a single line of standing type (audit §6
        // bans a category navbar in Aquila; §10 wants exactly these words).
        <header className="paper__masthead">
          <p className="paper__masthead-side">
            <span>{editionName}</span>
            <span>
              {t(locale, "aquila.volume", {
                volume: issue.volume,
                number: issue.number,
              })}
            </span>
          </p>
          <div className="paper__masthead-centre">
            <h1 className="paper__title">{t(locale, "aquila.title")}</h1>
            <p className="paper__strap">{t(locale, "aquila.strap")}</p>
          </div>
          {/* Stacked, one word per line. The side track is ~156px and the
              joined line needs ~290, so left as prose it wrapped with an
              orphaned separator. Split on the middot, which is the separator
              in every locale's copy; a locale that used another one would
              render as a single line rather than break. */}
          <p className="paper__masthead-side paper__masthead-side--end">
            {t(locale, "aquila.standfirst")
              .split("·")
              .map((word) => (
                <span key={word}>{word.trim()}</span>
              ))}
          </p>
        </header>
      ) : (
        <header className="paper__sectionhead">
          <h2>{page.title}</h2>
          <span className="paper__folio">{page.page_no}</span>
        </header>
      )}

      <div className="paper__rule">
        {/* The front page's masthead already carries these; a section page has
            no masthead, so the rule is where they belong there. */}
        {!isFront && (
          <span>
            {editionName} ·{" "}
            {t(locale, "aquila.volume", {
              volume: issue.volume,
              number: issue.number,
            })}
          </span>
        )}
        <span>
          {city
            ? t(locale, "aquila.dateline", { city, date: dateLine })
            : dateLine}
        </span>
        <span>{t(locale, "aquila.editionTime", { time: editionTime })}</span>
      </div>

      {page.slots.length === 0 ? (
        <p className="paper__empty">{t(locale, "aquila.pageEmpty")}</p>
      ) : (
        // The front page (audit §8): a left rail carrying the standing quote
        // and IN FOCUS; the dominant lead; an editorial right rail of
        // secondary stories; and, under all three, a lower row of further
        // major stories followed by TODAY'S HIGHLIGHTS. The page still has to
        // *end* - §35's landscape sheet is capped to the viewport height and
        // clips rather than scrolls (`.aquila__sheet { overflow: hidden }`) -
        // so the lower band is deliberately the plainest thing on the page:
        // no images, clamped to one line, the same restraint that already
        // applied to the right rail's second and third entries.
        //
        // A section page is a simpler thing and says so: one lead and its
        // columns, no rails to fill and nothing to pad them with.
        <div
          className={isFront ? "paper__body paper__body--front" : "paper__body"}
        >
          {isFront && (focus || briefs.length > 0) && (
            <section className="paper__focus">
              {/* §11's standing line. The paper's own motto, set as a
                  newspaper sets one - not a pull quote lifted from a story,
                  which this product has no body text to take. */}
              <p className="paper__motto">
                {t(locale, "aquila.motto")}
                <span>{t(locale, "aquila.mottoAttribution")}</span>
              </p>

              {focus && (
                <>
                  <h2 className="paper__label">
                    {t(locale, "aquila.inFocus")}
                  </h2>
                  {focus.article.image_url && (
                    <HalftoneImage
                      className="paper__focus-image"
                      src={focus.article.image_url}
                      width={600}
                      height={400}
                      sizes="(max-width: 46rem) 100vw, 11rem"
                      scale="sm"
                    />
                  )}
                  <h3 className="paper__focus-headline">
                    <Link href={`/${locale}/a/${focus.article.id}`}>
                      {focus.article.title}
                    </Link>
                  </h3>
                  <p className="paper__byline">
                    {focus.article.source_name}
                    <PageRefTag
                      pageRef={focus.page_ref}
                      sectionTitle={sectionTitle(focus.page_ref)}
                      locale={locale}
                      onGoTo={onGoTo}
                    />
                  </p>
                </>
              )}

              {/* §8 draws TODAY'S HIGHLIGHTS as part of a lower row this page
                  has no room for once a real lead is stretching the top row
                  to its own full height (measured: the lead alone is 531px
                  of a ~587px body budget at 1440x900, and the sheet clips
                  rather than scrolls). It stays here, where it already fit
                  before this chunk, and gains what §8 actually asked for
                  underneath it - numbered stories with page references. */}
              {briefs.length > 0 && (
                <>
                  <h2 className="paper__label">
                    {t(locale, "aquila.highlights")}
                  </h2>
                  <ol className="paper__brief-list">
                    {briefs.map((slot, index) => (
                      <li key={slot.position}>
                        {/* The number is the running order the composer set,
                            so it is content rather than decoration. */}
                        <span className="paper__brief-number">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        {/* One wrapper, not two direct children after the
                            numeral: the list item is a two-column grid
                            (number, text), and a third direct child would
                            wrap onto its own row instead of sitting beside
                            the headline it belongs to. */}
                        <span className="paper__brief-text">
                          <Link href={`/${locale}/a/${slot.article.id}`}>
                            {slot.article.title}
                          </Link>
                          <PageRefTag
                            pageRef={slot.page_ref}
                            sectionTitle={sectionTitle(slot.page_ref)}
                            locale={locale}
                            onGoTo={onGoTo}
                          />
                        </span>
                      </li>
                    ))}
                  </ol>
                </>
              )}
            </section>
          )}

          {lead && (
            <section className="paper__lead">
              {lead.article.image_url && (
                <HalftoneImage
                  className="paper__lead-image"
                  src={lead.article.image_url}
                  width={1200}
                  height={675}
                  sizes="(max-width: 46rem) 100vw, 40rem"
                  priority
                />
              )}
              <div className="paper__lead-text">
                <h2 className="paper__lead-headline">
                  <Link href={`/${locale}/a/${lead.article.id}`}>
                    {lead.article.title}
                  </Link>
                </h2>
                {lead.article.snippet && (
                  <p className="paper__deck">{lead.article.snippet}</p>
                )}
                <p className="paper__byline">{lead.article.source_name}</p>
              </div>
            </section>
          )}

          {(isFront ? rail : secondaries).length > 0 && (
            <section className="paper__highlights">
              {isFront && (
                <h2 className="paper__label">{t(locale, "aquila.moreNews")}</h2>
              )}
              <div className="paper__columns">
                {(isFront ? rail : secondaries).map((slot) => (
                  <div className="paper__column" key={slot.position}>
                    {/* A second and third picture on the page, which is what
                        the composer's image-aware selection is for. Not
                        priority: the lead is the LCP candidate, and marking
                        four images priority marks none of them. */}
                    {slot.article.image_url && (
                      <HalftoneImage
                        className="paper__column-image"
                        src={slot.article.image_url}
                        width={600}
                        height={400}
                        sizes="(max-width: 46rem) 100vw, 16rem"
                        scale="sm"
                      />
                    )}
                    <h3 className="paper__column-headline">
                      <Link href={`/${locale}/a/${slot.article.id}`}>
                        {slot.article.title}
                      </Link>
                    </h3>
                    {/* On the front page these are highlights - picture,
                        headline, outlet. The deck belongs to a section page,
                        where a column is the whole story rather than a
                        pointer to it, and where the page has the room. */}
                    {!isFront && slot.article.snippet && (
                      <p className="paper__column-deck">
                        {slot.article.snippet}
                      </p>
                    )}
                    <p className="paper__byline">{slot.article.source_name}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {isFront && lower.length > 0 && (
            // §8's lower row of further major stories. Headline and a page
            // reference only, no byline, no image, one line clamped: the
            // budget for this row is whatever the lead - the page's real
            // dominant story, and correctly the tallest thing on it - leaves
            // over, and at 1440x900 that measured to roughly 50px. A row this
            // constrained earns its place by staying exactly as plain as the
            // remaining space demands, rather than by being cut altogether.
            <section className="paper__lower">
              <div className="paper__lower-stories">
                {lower.map((slot) => (
                  <p className="paper__lower-story" key={slot.position}>
                    <Link href={`/${locale}/a/${slot.article.id}`}>
                      {slot.article.title}
                    </Link>
                    <PageRefTag
                      pageRef={slot.page_ref}
                      sectionTitle={sectionTitle(slot.page_ref)}
                      locale={locale}
                      onGoTo={onGoTo}
                    />
                  </p>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <footer className="paper__footer">{t(locale, "aquila.footer")}</footer>
    </article>
  );
}

/**
 * Third-pass audit §8/§46's "PAGE X" - a cross-reference from a front-page
 * story to the section page its own topic occupies in this same issue, not a
 * claim that the story itself continues. The product stores no body text, so
 * nothing here continues anywhere; what is real is that the topic has fuller
 * coverage a page away, the way a broadsheet's front page points a reader
 * inside rather than printing the whole story where it teases it.
 *
 * A button when the reader can act on it (`onGoTo` turns the page without a
 * navigation, the same call the contents panel makes), inert text otherwise -
 * this component renders wherever `IssuePaper` is used, and nothing about a
 * page reference requires a live reading session to be true.
 */
function PageRefTag({
  pageRef,
  sectionTitle,
  locale,
  onGoTo,
}: {
  pageRef: number | null | undefined;
  sectionTitle: string | null;
  locale: LocaleCode;
  onGoTo?: (page: number) => void;
}) {
  if (pageRef == null) return null;
  const label = sectionTitle
    ? t(locale, "aquila.pageRef.label", { section: sectionTitle, page: pageRef })
    : t(locale, "aquila.pageRef.labelPlain", { page: pageRef });
  const text = t(locale, "aquila.pageRef", { page: pageRef });

  if (!onGoTo) {
    return (
      <span className="paper__pageref" aria-label={label}>
        {text}
      </span>
    );
  }
  return (
    <button
      type="button"
      className="paper__pageref"
      onClick={() => onGoTo(pageRef)}
      aria-label={label}
    >
      {text}
    </button>
  );
}
