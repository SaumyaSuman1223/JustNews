import { redirect } from "next/navigation";

import { defaultLocale } from "@/lib/i18n";

/**
 * The real page moved to app/[locale]/privacy - a locale-agnostic /privacy
 * had a hardcoded `lang="en"` and a hardcoded /en/settings backlink
 * regardless of which locale linked to it, and sat outside the i18n
 * catalogue entirely. This keeps any bookmarked or externally linked
 * /privacy URL working by sending it to the default locale's copy, rather
 * than breaking it outright.
 */
export default function PrivacyRedirect() {
  redirect(`/${defaultLocale}/privacy`);
}
