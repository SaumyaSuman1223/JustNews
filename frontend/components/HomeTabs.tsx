import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

export type HomeTab = "forYou" | "trending" | "history" | "saved";

const TABS: { id: HomeTab; labelKey: `home.tabs.${HomeTab}`; requiresSignIn: boolean }[] = [
  { id: "forYou", labelKey: "home.tabs.forYou", requiresSignIn: false },
  { id: "trending", labelKey: "home.tabs.trending", requiresSignIn: false },
  { id: "history", labelKey: "home.tabs.history", requiresSignIn: true },
  { id: "saved", labelKey: "home.tabs.saved", requiresSignIn: true },
];

/**
 * The feed switcher below the hero. A server-rendered link set, not a
 * client-side tab widget - `?tab=` is a real URL for a real view, the same
 * pattern the feed's own `?cursor=` already uses, so a shared link opens on
 * the tab it was copied from.
 */
export function HomeTabs({
  locale,
  active,
  signedIn,
  basePath,
}: {
  locale: LocaleCode;
  active: HomeTab;
  signedIn: boolean;
  basePath: string;
}) {
  const visible = TABS.filter((tab) => !tab.requiresSignIn || signedIn);

  return (
    <nav className="home-tabs" aria-label={t(locale, "home.tabs.label")}>
      <ul>
        {visible.map((tab) => (
          <li key={tab.id}>
            <Link
              href={tab.id === "forYou" ? basePath : `${basePath}?tab=${tab.id}`}
              aria-current={active === tab.id ? "page" : undefined}
            >
              {t(locale, tab.labelKey)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
