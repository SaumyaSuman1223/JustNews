/**
 * The navigation model, defined once.
 *
 * The desktop rail and the mobile tab bar render the same destinations in
 * different shapes, and the fastest way to end up with a product whose phone
 * and desktop navigation disagree is to write the list twice. Both read this.
 *
 * The three primary destinations are the product's information architecture
 * (ADR 0011), not a menu: each answers a different question, which is why each
 * carries a subtitle in the rail. The cap of three is deliberate and is the
 * thing to defend - a fourth destination belongs inside one of these or it
 * does not belong in the chrome.
 */
import type { LocaleCode, MessageKey } from "@/lib/i18n";

export type NavGroup = "primary" | "secondary" | "tertiary";

export type NavItem = {
  /** Stable key, also the icon lookup and the i18n key suffix. */
  id: "home" | "aquila" | "desk" | "saved" | "search" | "settings" | "profile";
  group: NavGroup;
  /** Path after the locale prefix. Empty string is the locale root (Home). */
  path: string;
  /** i18n key for the label. Typed, so a missing string is a tsc failure. */
  labelKey: MessageKey;
  /** i18n key for the rail subtitle. Primary destinations only. */
  subtitleKey?: MessageKey;
  /** Hidden from a signed-out reader, who has nothing behind it. */
  requiresSession?: boolean;
  /** Shown in the mobile tab bar. Four is the most a tab bar holds well. */
  inTabBar?: boolean;
};

export const NAV_ITEMS: NavItem[] = [
  {
    id: "home",
    group: "primary",
    path: "",
    labelKey: "nav.home",
    subtitleKey: "nav.home.subtitle",
    inTabBar: true,
  },
  {
    id: "aquila",
    group: "primary",
    path: "/aquila",
    labelKey: "nav.aquila",
    subtitleKey: "nav.aquila.subtitle",
    inTabBar: true,
  },
  {
    id: "desk",
    group: "primary",
    path: "/desk",
    labelKey: "nav.desk",
    subtitleKey: "nav.desk.subtitle",
    inTabBar: true,
  },
  { id: "saved", group: "secondary", path: "/saved", labelKey: "nav.saved", requiresSession: true, inTabBar: true },
  { id: "search", group: "secondary", path: "/search", labelKey: "nav.search" },
  { id: "settings", group: "tertiary", path: "/settings", labelKey: "nav.settings", requiresSession: true },
];

export function hrefFor(item: NavItem, locale: LocaleCode): string {
  return `/${locale}${item.path}`;
}

/**
 * Whether `pathname` is inside this destination.
 *
 * Home matches only exactly - it is the locale root, and a prefix test would
 * mark it active on every page in the product. Everything else matches its
 * subtree, so `/en/desk/medtop:04000000` keeps My Desk lit.
 */
export function isActive(item: NavItem, pathname: string, locale: LocaleCode): boolean {
  const href = hrefFor(item, locale);
  if (item.path === "") return pathname === href || pathname === `${href}/`;
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Redirects for the routes ADR 0011 renamed, longest path first so
 * `/topics/x` is tested before `/topics`.
 *
 * Permanent (308): the old paths are not coming back, the method is preserved,
 * and crawlers update rather than keeping both in the index.
 */
export const RENAMED_ROUTES: { from: string; to: string }[] = [
  { from: "/topics", to: "/desk" },
  { from: "/explore", to: "/aquila" },
];
