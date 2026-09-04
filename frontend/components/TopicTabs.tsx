import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

export type TopicTab = "latest" | "timeline" | "keyDevelopments" | "perspectives" | "analysis";

const TABS: { id: TopicTab; labelKey: `desk.tabs.${TopicTab}` }[] = [
  { id: "latest", labelKey: "desk.tabs.latest" },
  { id: "timeline", labelKey: "desk.tabs.timeline" },
  { id: "keyDevelopments", labelKey: "desk.tabs.keyDevelopments" },
  { id: "perspectives", labelKey: "desk.tabs.perspectives" },
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
              href={tab.id === "latest" ? basePath : `${basePath}?tab=${tab.id}`}
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
