import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Rendered only when the reader has not yet decided (app/[locale]/layout.tsx
 * checks getConsentState() before mounting this at all - once they choose,
 * it stops rendering, it does not just hide).
 *
 * Both buttons are `.button--secondary` - the same weight, deliberately.
 * GDPR requires refusal to be exactly as easy as acceptance; a de-emphasised
 * Decline next to a filled, primary Accept is the textbook version of the
 * dark pattern that requirement exists to rule out.
 *
 * Two plain form posts to app/api/consent/route.ts, no client component and
 * no Server Action: a consent choice should keep working with JavaScript
 * off, and the route's own comment says why the Server Action it replaced
 * left the banner on screen.
 */
export function ConsentBanner({ locale }: { locale: LocaleCode }) {
  return (
    <div className="consent-banner" role="region" aria-label={t(locale, "consent.label")}>
      <div className="consent-banner__inner">
        <p className="consent-banner__text">
          {t(locale, "consent.body")}{" "}
          <Link href={`/${locale}/privacy`}>{t(locale, "settings.privacyPolicy")}</Link>
        </p>
        <div className="consent-banner__actions">
          <form action="/api/consent" method="post">
            <input type="hidden" name="choice" value="denied" />
            <button type="submit" className="button button--secondary">
              {t(locale, "consent.decline")}
            </button>
          </form>
          <form action="/api/consent" method="post">
            <input type="hidden" name="choice" value="granted" />
            <button type="submit" className="button button--secondary">
              {t(locale, "consent.accept")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
