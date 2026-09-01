import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";

import { getLocale, isLocaleCode, locales } from "@/lib/i18n";

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
    title: "JustNews",
    description: "Personalised, multilingual news.",
    // hreflang across every locale, so search engines serve the right one.
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(locales.map((l) => [l.htmlLang, `/${l.code}`])),
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

  return (
    // dir here is what makes every logical CSS property mirror. It is the only
    // thing standing between us and a stylesheet fork for Arabic.
    <html lang={active.htmlLang} dir={active.dir}>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <div className="shell">
          <header className="masthead">
            <Link href={`/${active.code}`} className="wordmark">
              Just<span>News</span>
            </Link>
            <nav aria-label="Language">
              <ul className="locale-switcher">
                {locales.map((option) => (
                  <li key={option.code}>
                    <Link
                      href={`/${option.code}`}
                      lang={option.htmlLang}
                      aria-current={option.code === active.code}
                    >
                      {option.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </header>
          <main id="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
