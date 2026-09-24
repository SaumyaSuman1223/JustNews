import Link from "next/link";

import { AccountMenu } from "@/components/AccountMenu";
import { SearchIcon } from "@/components/icons";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { NAV_ICONS } from "@/components/navIcons";
import { SidebarCollapse } from "@/components/SidebarControls";
import { NAV_ITEMS, hrefFor, isActive, type NavGroup } from "@/lib/navigation";
import { t, type getLocale } from "@/lib/i18n";

/**
 * The application's left panel: search, the destinations, and the account.
 *
 * Everything in it comes from `NAV_ITEMS` (lib/navigation.ts), so a new place
 * is one entry there rather than a change here. Rendered on the server with
 * the pathname the middleware forwards, so the active state costs no client
 * JavaScript; the only interactive parts are the collapse toggle, the account
 * menu and, on a phone, the drawer (SidebarControls).
 *
 * Collapsed, it is an icon column: labels are hidden visually but stay each
 * link's accessible name, and each link carries a `title` for the pointer.
 * The choice is a cookie the layout reads, so a reload never flashes the
 * other width.
 */
export function Sidebar({
  active,
  pathname,
  search,
  signedIn,
  email,
  hasBetaAccess,
  collapsed,
}: {
  active: ReturnType<typeof getLocale>;
  pathname: string;
  search: string;
  signedIn: boolean;
  email: string | null;
  hasBetaAccess: boolean;
  collapsed: boolean;
}) {
  const locale = active.code;
  const visible = NAV_ITEMS.filter((item) => !item.requiresSession || signedIn);
  const groups = (["primary", "secondary", "tertiary"] as const satisfies readonly NavGroup[])
    .map((name) => ({ name, items: visible.filter((item) => item.group === name) }))
    .filter((group) => group.items.length > 0);

  return (
    <aside
      id="sidebar"
      className="sidebar"
      data-collapsed={collapsed || undefined}
      aria-label={t(locale, "sidebar.label")}
    >
      <div className="sidebar__head">
        <Link href={`/${locale}`} className="sidebar__wordmark" aria-label="JustNews">
          <span className="sidebar__wordmark-full" aria-hidden="true">
            Just<span>News</span>
          </span>
          <span className="sidebar__wordmark-mark" aria-hidden="true">
            JN
          </span>
        </Link>
        <SidebarCollapse locale={locale} initialCollapsed={collapsed} />
      </div>

      {/* A plain GET form: search works before hydration and with JS off,
          and lands on the search page with its type-ahead and filters. */}
      <form className="sidebar__search" action={`/${locale}/search`} method="get" role="search">
        <SearchIcon className="sidebar__search-icon" />
        <input
          type="search"
          name="q"
          className="sidebar__search-input"
          placeholder={t(locale, "sidebar.search")}
          aria-label={t(locale, "sidebar.search")}
          autoComplete="off"
          enterKeyHint="search"
        />
      </form>

      <nav className="sidebar__nav" aria-label={t(locale, "nav.primary")}>
        {groups.map(({ name, items }) => (
          <ul className="sidebar__group" key={name}>
            {items.map((item) => {
              const Icon = NAV_ICONS[item.id];
              const label = t(locale, item.labelKey);
              return (
                <li key={item.id} data-nav={item.id}>
                  <Link
                    href={hrefFor(item, locale)}
                    className="sidebar__link"
                    aria-current={isActive(item, pathname, locale) ? "page" : undefined}
                    data-label={label}
                    title={collapsed ? label : undefined}
                  >
                    <Icon className="sidebar__icon" />
                    <span className="sidebar__label">{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        ))}
      </nav>

      <div className="sidebar__foot">
        <ul className="sidebar__small">
          <li>
            <Link href={`/${locale}/how-it-works`}>{t(locale, "nav.howItWorks")}</Link>
          </li>
          <li>
            <Link href={`/${locale}/display`}>{t(locale, "nav.display")}</Link>
          </li>
          <li>
            <Link href={`/${locale}/privacy`}>{t(locale, "nav.privacy")}</Link>
          </li>
          <li>
            <Link href={`/${locale}/feedback`}>{t(locale, "nav.feedback")}</Link>
          </li>
        </ul>
        <div className="sidebar__locale">
          <LocaleSwitcher active={active} pathname={pathname} search={search} />
        </div>
        <div className="sidebar__account">
          <AccountMenu locale={locale} email={email} hasBetaAccess={hasBetaAccess} />
        </div>
      </div>
    </aside>
  );
}
