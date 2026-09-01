import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";

import { AccountMenu } from "@/components/AccountMenu";
import { SearchBox } from "@/components/SearchBox";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, locales } from "@/lib/i18n";
import { getSession } from "@/lib/session";

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
  // Reading the session here - once, for the whole shell - is what makes this
  // layout request-dynamic rather than static. That is the correct trade for
  // a header that has to show a real account state instead of a generic one.
  const session = await getSession();
  const hasBetaAccess = session
    ? ((await getMe({ accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }))
        ?.has_beta_access ?? false)
    : false;

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
            <nav className="masthead-nav" aria-label="Primary">
              <ul className="masthead-links">
                <li>
                  <Link href={`/${active.code}/topics`}>Topics</Link>
                </li>
                {session && (
                  <li>
                    <Link href={`/${active.code}/saved`}>Saved</Link>
                  </li>
                )}
              </ul>
              <SearchBox locale={active.code} />
              <AccountMenu
                locale={active.code}
                email={session?.email ?? null}
                hasBetaAccess={hasBetaAccess}
              />
            </nav>
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
          <footer className="site-footer">
            <Link href="/privacy">Privacy</Link>
          </footer>
        </div>
      </body>
    </html>
  );
}
