import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { cookies, headers } from "next/headers";

import { MobileTabBar } from "@/components/MobileTabBar";
import { ReaderShortcuts } from "@/components/ReaderShortcuts";
import { Sidebar } from "@/components/Sidebar";
import { MobileTopBar } from "@/components/SidebarControls";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";
import { SIDEBAR_COOKIE } from "@/lib/sidebarCookie";

/**
 * The application shell: the sidebar (search, destinations, account), the
 * phone's top bar and tab bar, and the page.
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
  // In parallel: the session is a network round trip to Supabase Auth, and
  // nothing about the headers or cookies waits on it.
  const [session, requestHeaders, cookieStore, browsingSessionId] = await Promise.all([
    getSession(),
    headers(),
    cookies(),
    getBrowsingSessionId(),
  ]);
  const hasBetaAccess = session
    ? ((await getMe({ accessToken: session.accessToken, sessionId: browsingSessionId }))
        ?.has_beta_access ?? false)
    : false;
  const pathname = requestHeaders.get("x-pathname") ?? `/${active.code}`;
  const search = requestHeaders.get("x-search") ?? "";
  const collapsed = cookieStore.get(SIDEBAR_COOKIE)?.value === "collapsed";

  return (
    <>
      <a className="skip-link" href="#main">
        {t(active.code, "skip.toContent")}
      </a>
      <div className="app-shell">
        <Sidebar
          active={active}
          pathname={pathname}
          search={search}
          signedIn={Boolean(session)}
          email={session?.email ?? null}
          hasBetaAccess={hasBetaAccess}
          collapsed={collapsed}
        />
        <div className="app-shell__main">
          <MobileTopBar locale={active.code} />
          {/* tabIndex={-1}: without it, activating the skip link scrolls the
              viewport but never actually moves keyboard focus here, which
              defeats what a skip link is for. */}
          <main id="main" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
      <MobileTabBar locale={active.code} pathname={pathname} signedIn={Boolean(session)} />
      <ReaderShortcuts locale={active.code} />
    </>
  );
}
