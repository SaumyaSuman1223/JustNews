import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

export type TopicTab = "understand" | "latest" | "analysis";

/**
 * Three tabs, not six.
 *
 * Timeline, Key Developments and Perspectives were separate tabs, which meant
 * a reader had to already know what each one held to find any of it. Audit
 * §26 asks for them as modules on one page instead, and Understand is that
 * page - so the tabs that used to split them are gone rather than duplicated
 * beside it. An old `?tab=timeline` link now falls through to Understand,
 * which contains the timeline.
 */
const TABS: { id: TopicTab; labelKey: `desk.tabs.${TopicTab}` }[] = [
  { id: "understand", labelKey: "desk.tabs.understand" },
  { id: "latest", labelKey: "desk.tabs.latest" },
  { id: "analysis", labelKey: "desk.tabs.analysis" },
];

export function TopicTabs({
  locale,
  active,
  basePath,
}: {
  locale: LocaleCode;
  active: TopicTab;
  basePath: string;
}) {
  return (
    <nav className="home-tabs" aria-label={t(locale, "desk.tabs.label")}>
      <ul>
        {TABS.map((tab) => (
          <li key={tab.id}>
            <Link
              href={tab.id === "understand" ? basePath : `${basePath}?tab=${tab.id}`}
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
