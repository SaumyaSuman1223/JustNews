"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/**
 * A thin bar at the top of the viewport that starts the instant an internal
 * link is clicked and completes once the new route has actually rendered.
 *
 * The problem this exists to fix: a Server Component route has no built-in
 * "navigating" signal in the App Router, so between the click and the new
 * page appearing, nothing on screen acknowledges the click happened at all -
 * on a slow connection or a cold-started API (this app's own Render free
 * tier can take ~22s to wake, see lib/api.ts) that reads as a broken link,
 * not a slow one.
 *
 * No progress library: the App Router gives no real completion percentage to
 * report, so a hand-rolled indeterminate sweep (the same technique
 * nprogress-style bars use) says exactly as much as is actually known - "a
 * navigation is in flight" - rather than fabricating a fake percentage.
 *
 * Two signals, not one:
 *  - a *capture-phase* click listener starts the bar the instant a
 *    same-origin, unmodified left-click on an in-app link fires - before the
 *    network request even goes out, and critically before `next/link`'s own
 *    bubble-phase handler calls `preventDefault()`. A bubble-phase listener
 *    here would see `event.defaultPrevented` already true for every real
 *    Link click (that is how Link stops the native navigation and starts its
 *    own), which was measured live: the bar never started at all;
 *  - `usePathname`/`useSearchParams` changing is React's own confirmation
 *    that the new route has committed, which is what ends the bar. That
 *    effect also runs on first mount, when there is nothing to end, which is
 *    harmless: the bar starts idle either way.
 */
export function NavigationProgress() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [state, setState] = useState<"idle" | "loading" | "done">("idle");
  const doneTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      const anchor = (event.target as Element | null)?.closest("a");
      if (!anchor || !(anchor instanceof HTMLAnchorElement)) return;
      if (anchor.target && anchor.target !== "_self") return;
      if (anchor.hasAttribute("download")) return;

      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
        return;
      }

      let url: URL;
      try {
        url = new URL(href, window.location.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;
      // A link to the exact page already showing (including a bare "#"
      // anchor caught above) has nothing to wait for.
      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        return;
      }

      if (doneTimeout.current) clearTimeout(doneTimeout.current);
      setState("loading");
    }

    document.addEventListener("click", onClick, { capture: true });
    return () => document.removeEventListener("click", onClick, { capture: true });
  }, []);

  useEffect(() => {
    // Not a synchronous setState in the effect body (React's
    // set-state-in-effect lint rule flags that as a cascading-render risk):
    // scheduled on the next tick instead, and reads `state` fresh via the
    // updater so a mount-time run (nothing was loading) is a no-op.
    const id = setTimeout(() => {
      setState((current) => (current === "loading" ? "done" : current));
    }, 0);
    return () => clearTimeout(id);
  }, [pathname, searchParams]);

  useEffect(() => {
    if (state !== "done") return;
    // Lets the bar visibly reach 100% before it fades, rather than jumping
    // straight from "sweeping" to gone - the completion is part of the
    // feedback, not just the disappearance.
    doneTimeout.current = setTimeout(() => setState("idle"), 220);
    return () => {
      if (doneTimeout.current) clearTimeout(doneTimeout.current);
    };
  }, [state]);

  return <div className="nav-progress" data-state={state} aria-hidden="true" />;
}
