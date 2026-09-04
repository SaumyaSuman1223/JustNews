import Link from "next/link";

import {
  AquilaIcon,
  DeskIcon,
  HomeIcon,
  ProfileIcon,
  SavedIcon,
  SearchIcon,
  SettingsIcon,
} from "@/components/icons";
import { NAV_ITEMS, hrefFor, isActive, type NavGroup, type NavItem } from "@/lib/navigation";
import { t, type LocaleCode } from "@/lib/i18n";

const ICONS = {
  home: HomeIcon,
  aquila: AquilaIcon,
  desk: DeskIcon,
  saved: SavedIcon,
  search: SearchIcon,
  settings: SettingsIcon,
  profile: ProfileIcon,
} as const;

/**
 * The desktop navigation rail.
 *
 * Rendered on the server with the pathname the middleware forwarded, so the
 * active state costs no client JavaScript - the rail is the most-rendered
 * component in the product and has no reason to hydrate.
 *
 * Primary destinations carry their subtitle; secondary and tertiary do not.
 * That difference is the hierarchy - three things that are the product, and
 * four that support it - and it is why the groups are separated by a rule
 * rather than by a heading nobody would read twice.
 */
export function PrimaryNav({
  locale,
  pathname,
  signedIn,
}: {
  locale: LocaleCode;
  pathname: string;
  signedIn: boolean;
}) {
  const visible = NAV_ITEMS.filter((item) => !item.requiresSession || signedIn);
  // Non-empty by construction after the filter, but the type says otherwise,
  // so the key comes from the group name rather than from `group[0]`.
  const groups: { name: NavGroup; items: NavItem[] }[] = (
    ["primary", "secondary", "tertiary"] as const
  )
    .map((name) => ({ name, items: visible.filter((i) => i.group === name) }))
    .filter((g) => g.items.length > 0);

  return (
    <nav className="rail-nav" aria-label={t(locale, "nav.primary")}>
      {groups.map(({ name, items }, index) => (
        <ul className="rail-group" key={name} data-first={index === 0 || undefined}>
          {items.map((item) => {
            const IconComponent = ICONS[item.id];
            const active = isActive(item, pathname, locale);
            return (
              <li key={item.id}>
                <Link
                  href={hrefFor(item, locale)}
                  className="rail-link"
                  // aria-current is what tells a screen reader which
                  // destination it is in. The brass indicator says it to
                  // everyone else, and neither is the only signal - the
                  // design system forbids conveying state by colour alone.
                  aria-current={active ? "page" : undefined}
                >
                  <IconComponent className="rail-link__icon" />
                  <span className="rail-link__text">
                    <span className="rail-link__label">{t(locale, item.labelKey)}</span>
                    {item.subtitleKey && (
                      <span className="rail-link__subtitle">{t(locale, item.subtitleKey)}</span>
                    )}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      ))}
    </nav>
  );
}
