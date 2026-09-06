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
        <header className="masthead">
          <Link href={`/${active.code}`} className="wordmark">
            Just<span>News</span>
            <span className="wordmark__tagline">{t(active.code, "site.tagline")}</span>
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
          <LocaleSwitcher active={active} pathname={pathname} search={search} />
          <p className="masthead-sign">{t(active.code, "site.sign")}</p>
        </header>
        {/* tabIndex={-1}: without it, activating the skip link scrolls the
            viewport but never actually moves keyboard focus here, which
            defeats what a skip link is for. Not in the tab order itself -
            only reachable as a fragment-navigation target. */}
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer className="site-footer">
          <Link href={`/${active.code}/privacy`}>{t(active.code, "nav.privacy")}</Link>
          <Link href={`/${active.code}/feedback`}>{t(active.code, "nav.feedback")}</Link>
        </footer>
      </div>
      <MobileTabBar locale={active.code} pathname={pathname} signedIn={Boolean(session)} />
    </>
  );
}
