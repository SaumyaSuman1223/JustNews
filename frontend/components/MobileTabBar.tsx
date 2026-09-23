import Link from "next/link";

import { NAV_ICONS } from "@/components/navIcons";
import { NAV_ITEMS, hrefFor, isActive } from "@/lib/navigation";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * The mobile bottom tab bar.
 *
 * Below the rail's breakpoint the navigation moves to the bottom of the
 * viewport, where a thumb reaches it - the design direction's rule that a
 * phone gets its own navigation rather than a shrunken desktop one.
 *
 * Up to four tabs, from the same model the sidebar reads; everything else -
 * history, settings, the account - is in the sidebar, which opens as a
 * drawer from the top bar on a phone.
 */
export function MobileTabBar({
  locale,
  pathname,
  signedIn,
}: {
  locale: LocaleCode;
  pathname: string;
  signedIn: boolean;
}) {
  const items = NAV_ITEMS.filter(
    (item) => item.inTabBar && (!item.requiresSession || signedIn),
  ).slice(0, 4);

  return (
    <nav className="tabbar" aria-label={t(locale, "nav.primary")}>
      <ul className="tabbar__list">
        {items.map((item) => {
          const IconComponent = NAV_ICONS[item.id];
          const active = isActive(item, pathname, locale);
          return (
            <li key={item.id}>
              <Link
                href={hrefFor(item, locale)}
                className="tabbar__link"
                aria-current={active ? "page" : undefined}
              >
                <IconComponent className="tabbar__icon" />
                <span className="tabbar__label">{t(locale, item.labelKey)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
