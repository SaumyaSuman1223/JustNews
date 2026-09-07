"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTransition, type ReactNode } from "react";

import { t, type LocaleCode } from "@/lib/i18n";

export type TopicTab = "understand" | "latest" | "analysis";

const TABS: { id: TopicTab; labelKey: `desk.tabs.${TopicTab}` }[] = [
  { id: "understand", labelKey: "desk.tabs.understand" },
  { id: "latest", labelKey: "desk.tabs.latest" },
  { id: "analysis", labelKey: "desk.tabs.analysis" },
];

/**
 * Three tabs, not six - and, per audit §35, My Desk's own signature gesture:
 * "open a topic and progressively reveal context." Understand already put
 * Timeline, Key Developments and Perspectives on one page instead of three
 * tabs to hunt through; what was left was that switching tabs at all was a
 * hard navigation - a blank flash, then the next page - which is exactly the
 * "page load" feeling §35 is asking this surface to move past.
 *
 * The fix is not a decorative entrance animation (design-system.md bans
 * those outright: "no entrance animations on load"). It is a real state a
 * reader causes and can see: `children` (the tab body) dims in place, via
 * design-system.md's Standard tier (240ms, "navigation, panels, menus"),
 * while the next tab's content streams in behind it, then sharpens back to
 * full opacity the instant it's ready - motion reporting a state that
 * actually changed, not motion for its own sake.
 *
 * Still real `<Link>`s throughout, not buttons: a plain, unmodified left
 * click intercepts the navigation to animate it (mirroring
 * NavigationProgress's own guard), but a modifier click - open in new tab,
 * copy link, middle-click - falls through to the browser exactly as it
 * would on any other link. `router.push` keeps the URL real and
 * bookmarkable; the server component underneath does the same work it
 * always did.
 */
export function TopicTabs({
  locale,
  active,
  basePath,
  children,
}: {
  locale: LocaleCode;
  active: TopicTab;
  basePath: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function go(event: React.MouseEvent<HTMLAnchorElement>, href: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    startTransition(() => {
      router.push(href, { scroll: false });
    });
  }

  return (
    <>
      <nav className="home-tabs" aria-label={t(locale, "desk.tabs.label")}>
        <ul>
          {TABS.map((tab) => {
            const href = tab.id === "understand" ? basePath : `${basePath}?tab=${tab.id}`;
            return (
              <li key={tab.id}>
                <Link
                  href={href}
                  aria-current={active === tab.id ? "page" : undefined}
                  onClick={(event) => go(event, href)}
                >
                  {t(locale, tab.labelKey)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="topic-unfold" data-pending={pending || undefined} aria-busy={pending}>
        {children}
      </div>
    </>
  );
}
