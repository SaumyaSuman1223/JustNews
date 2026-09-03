import Link from "next/link";

import { CoverageChips } from "@/components/CoverageChips";
import type { Blindspot } from "@/lib/api";
import { type LocaleCode, t } from "@/lib/i18n";

/**
 * Stories being reported right now, but not in a language this reader reads.
 *
 * Ground News's Blindspot reframed around language instead of politics. The
 * reframing is what makes it honest: this counts articles that exist rather
 * than scoring anyone's politics, and it is only answerable because the dedup
 * layer clusters across languages - so "the same story, elsewhere" is a fact
 * about the corpus, not a judgement about a publisher.
 */
export function BlindspotRail({
  blindspots,
  locale,
}: {
  blindspots: Blindspot[];
  locale: LocaleCode;
}) {
  if (blindspots.length === 0) return null;

  return (
    <section className="blindspot" aria-labelledby="blindspot-heading">
      <h2 id="blindspot-heading" className="blindspot__heading">
        {t(locale, "blindspot.heading")}
      </h2>
      <p className="blindspot__note">{t(locale, "blindspot.note")}</p>
      <ul className="blindspot__list">
        {blindspots.map((item) => (
          <li key={item.story.id} className="blindspot__item">
            <h3 className="blindspot__title">
              <Link href={`/${locale}/story/${item.story.id}`}>{item.story.title}</Link>
            </h3>
            <CoverageChips coverage={item.coverage} locale={locale} />
          </li>
        ))}
      </ul>
    </section>
  );
}
