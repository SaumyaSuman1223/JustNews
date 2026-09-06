import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import { notFound } from "next/navigation";

import { ConsentBanner } from "@/components/ConsentBanner";
import { NavigationProgress } from "@/components/NavigationProgress";
import { getConsentState } from "@/lib/consent";
import { fontVariables } from "@/lib/fonts";
import { getLocale, isLocaleCode, locales, t } from "@/lib/i18n";

/**
 * Everything every route shares, and nothing else.
 *
 * The application shell used to live here, which meant Aquila - a newspaper -
 * rendered inside a sidebar, a mobile tab bar and a site footer. A publication
 * cannot read as a publication while wearing an app's chrome, so the shell
 * moved down into `(app)/layout.tsx` and Aquila took `(reader)/layout.tsx`.
 *
 * Route groups do not appear in URLs: `/en/aquila` and `/en/desk` are exactly
 * the paths they were before. The parentheses are the whole mechanism.
 *
 * What stays here is what is true of both: the document element (so `dir` and
 * the font variables are set once), the navigation indicator, and consent -
 * which is a legal obligation, not a piece of app furniture, and must appear
 * on a reader's first page whichever one that is.
 */

export function generateStaticParams() {
  return locales.map((locale) => ({ locale: locale.code }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: { default: "JustNews", template: "%s · JustNews" },
    description: t(isLocaleCode(locale) ? locale : "en", "site.description"),
    // hreflang across every locale, so search engines serve the right one.
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(locales.map((l) => [l.htmlLang, `/${l.code}`])),
      types: { "application/rss+xml": `/${locale}/rss.xml` },
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const consent = await getConsentState();

  return (
    // dir here is what makes every logical CSS property mirror. It is the only
    // thing standing between us and a stylesheet fork for Arabic.
    <html lang={active.htmlLang} dir={active.dir} className={fontVariables}>
      <body>
        <Suspense fallback={null}>
          <NavigationProgress />
        </Suspense>
        {children}
        {consent === null && <ConsentBanner locale={active.code} />}
      </body>
    </html>
  );
}
