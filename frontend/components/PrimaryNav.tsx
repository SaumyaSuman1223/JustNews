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
 * Audit §14 makes it icons only, in a 52-60px rail. The label is still in the
 * DOM and still the link's accessible name - it is revealed on hover and on
 * keyboard focus as a tooltip, and hidden with opacity rather than
 * `display: none` or `visibility` so it never leaves the accessibility tree.
 * A tooltip that is the *only* name is the usual way an icon rail fails; this
 * one is a name that happens to be drawn as a tooltip.
 *
 * The subtitles are gone. They were the argument for a 320px column, and
 * §14's "no large labels" is the argument against one.
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
                  <span className="rail-link__label">{t(locale, item.labelKey)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      ))}
    </nav>
  );
}
