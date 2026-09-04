import Link from "next/link";

import { setConsentAction } from "@/lib/actions";
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
 * Two plain `<form action={...}>` submissions, no client component: matches
 * how every other one-shot choice in this app already works
 * (completeOnboardingAction, redeemInviteAction), and a consent choice is
 * exactly the kind of action that should keep working with JavaScript off.
 */
export function ConsentBanner({ locale }: { locale: LocaleCode }) {
  const grant = setConsentAction.bind(null, "granted");
  const deny = setConsentAction.bind(null, "denied");

  return (
    <div className="consent-banner" role="region" aria-label={t(locale, "consent.label")}>
      <div className="consent-banner__inner">
        <p className="consent-banner__text">
          {t(locale, "consent.body")}{" "}
          <Link href={`/${locale}/privacy`}>{t(locale, "settings.privacyPolicy")}</Link>
        </p>
        <div className="consent-banner__actions">
          <form action={deny}>
            <button type="submit" className="button button--secondary">
              {t(locale, "consent.decline")}
            </button>
          </form>
          <form action={grant}>
            <button type="submit" className="button button--secondary">
              {t(locale, "consent.accept")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
