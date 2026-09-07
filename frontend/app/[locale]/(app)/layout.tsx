import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import Link from "next/link";

import { AccountMenu } from "@/components/AccountMenu";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { MobileTabBar } from "@/components/MobileTabBar";
import { PrimaryNav } from "@/components/PrimaryNav";
import { SearchBox } from "@/components/SearchBox";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

/**
 * The application shell: rail, account, locale switcher, mobile tabs, footer.
 *
 * This is every destination except Aquila, which reads under
 * `(reader)/layout.tsx` instead. The split is why the session read below is
 * here rather than one level up - the reader has no account menu to fill, so
 * it should not pay for a `getMe` round trip to render a newspaper.
 */
export default async function AppShellLayout({
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
  const requestHeaders = await headers();
  const pathname = requestHeaders.get("x-pathname") ?? `/${active.code}`;
  const search = requestHeaders.get("x-search") ?? "";

  return (
    <>
      <a className="skip-link" href="#main">
        {t(active.code, "skip.toContent")}
      </a>
      <div className="shell">
        {/* Audit §14/§29: on desktop this is a 56px icon rail, not a 320px
            column of labelled links. The wordmark shrinks to a monogram, the
            language control moves to the footer, and the search field is gone
            because Search is a destination in the rail. What is left is the
            product's seven places and the account - which is the whole point
            of §29's complaint that the navigation was carrying too much. */}
        <header className="masthead">
          <Link href={`/${active.code}`} className="wordmark" aria-label="JustNews">
            <span className="wordmark__full">
              Just<span className="wordmark__accent">News</span>
            </span>
            {/* aria-hidden: the link is named by aria-label, so the monogram
                would otherwise be announced as a second, meaningless "JN". */}
            <span className="wordmark__mark" aria-hidden="true">
              JN
            </span>
          </Link>
          <PrimaryNav locale={active.code} pathname={pathname} signedIn={Boolean(session)} />
          <div className="masthead-tools">
            <SearchBox locale={active.code} />
            <AccountMenu
              locale={active.code}
              email={session?.email ?? null}
              hasBetaAccess={hasBetaAccess}
            />
          </div>
        </header>
        {/* tabIndex={-1}: without it, activating the skip link scrolls the
            viewport but never actually moves keyboard focus here, which
            defeats what a skip link is for. Not in the tab order itself -
            only reachable as a fragment-navigation target. */}
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        {/* Audit §30: one quiet line, not a second copy of the navigation.
            The identity and the language control live here now - both were in
            the rail, and neither survives a 56px column. */}
        <footer className="site-footer">
          <p className="site-footer__identity">
            <span className="site-footer__mark">JustNews</span>
            <span className="site-footer__tagline">{t(active.code, "site.tagline")}</span>
          </p>
          <div className="site-footer__line">
            <Link href={`/${active.code}/privacy`}>{t(active.code, "nav.privacy")}</Link>
            <Link href={`/${active.code}/feedback`}>{t(active.code, "nav.feedback")}</Link>
            <LocaleSwitcher active={active} pathname={pathname} search={search} />
          </div>
        </footer>
      </div>
      <MobileTabBar locale={active.code} pathname={pathname} signedIn={Boolean(session)} />
    </>
  );
}
