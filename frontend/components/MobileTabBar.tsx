import Link from "next/link";

import { AquilaIcon, DeskIcon, HomeIcon, SavedIcon, SearchIcon } from "@/components/icons";
import { NAV_ITEMS, hrefFor, isActive } from "@/lib/navigation";
import { t, type LocaleCode } from "@/lib/i18n";

const ICONS = {
  home: HomeIcon,
  aquila: AquilaIcon,
  desk: DeskIcon,
  saved: SavedIcon,
  search: SearchIcon,
} as const;

/**
 * The mobile bottom tab bar.
 *
 * Below the rail's breakpoint the navigation moves to the bottom of the
 * viewport, where a thumb reaches it - the design direction's rule that a
 * phone gets its own navigation rather than a shrunken desktop one.
 *
 * Four tabs, from the same model the rail reads. A signed-out reader has no
 * Saved, so Search takes the fourth slot rather than the bar rendering three
 * items and a gap: `inTabBar` marks the candidates and this takes the first
 * four that are actually visible.
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
    (item) => (item.inTabBar || item.id === "search") && (!item.requiresSession || signedIn),
  ).slice(0, 4);

  return (
    <nav className="tabbar" aria-label={t(locale, "nav.primary")}>
      <ul className="tabbar__list">
        {items.map((item) => {
          const IconComponent = ICONS[item.id as keyof typeof ICONS];
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
