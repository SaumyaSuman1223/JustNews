"use client";

import { useEffect, type RefObject } from "react";

/**
 * What a reader did with a served card, reported from the browser: a click,
 * and whether the card was on screen at all (ADR 0015). Both go through this
 * app's own routes (app/api/click, app/api/views), which add the session and
 * drop everything without analytics consent - so nothing here needs to know
 * whether the reader consented.
 */

export interface ClickReport {
  articleId: number;
  surface: string;
  /** The card's place in the feed as the ranker served it. */
  position?: number;
  impressionId?: number;
  topicId?: string;
  locale?: string;
}

/** Fire-and-forget, never delaying the navigation it accompanies. */
export function reportClick(report: ClickReport): void {
  void fetch("/api/click", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(report),
    keepalive: true,
  });
}

export type ViewSlot = "lead" | "wide" | "card" | "row" | "page";

interface ViewReport {
  impressionId: number;
  renderedPosition: number;
  slot: ViewSlot;
}

/** Half the card visible, for a second: the common viewability rule, and
 * long enough that a card scrolled straight past does not count as seen. */
const VISIBLE_SHARE = 0.5;
const VISIBLE_MS = 1000;
const FLUSH_MS = 2000;
const MAX_BATCH = 100;

const queue: ViewReport[] = [];
const reported = new Set<number>();
let timer: ReturnType<typeof setTimeout> | null = null;
let listening = false;

function flush(): void {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  while (queue.length > 0) {
    const batch = queue.splice(0, MAX_BATCH);
    const body = JSON.stringify({ views: batch });
    // sendBeacon survives the page being hidden or unloaded; fetch is the
    // fallback where it is missing or refuses the payload.
    const sent =
      typeof navigator.sendBeacon === "function" &&
      navigator.sendBeacon("/api/views", new Blob([body], { type: "application/json" }));
    if (!sent) {
      void fetch("/api/views", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
        keepalive: true,
      });
    }
  }
}

function enqueue(view: ViewReport): void {
  if (reported.has(view.impressionId)) return;
  reported.add(view.impressionId);
  queue.push(view);
  if (!listening) {
    listening = true;
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flush();
    });
    window.addEventListener("pagehide", flush);
  }
  if (queue.length >= MAX_BATCH) flush();
  else if (!timer) timer = setTimeout(flush, FLUSH_MS);
}

/** Reports the served card at `ref` once it has been on screen - only when
 * it was served under a logged impression (`view` is null otherwise). */
export function useViewReport(ref: RefObject<HTMLElement | null>, view: ViewReport | null): void {
  const impressionId = view?.impressionId ?? null;
  const renderedPosition = view?.renderedPosition ?? 0;
  const slot = view?.slot ?? "card";
  useEffect(() => {
    const element = ref.current;
    if (impressionId === null || !element || reported.has(impressionId)) return;
    if (typeof IntersectionObserver === "undefined") return;
    let pending: ReturnType<typeof setTimeout> | null = null;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.some((entry) => entry.intersectionRatio >= VISIBLE_SHARE);
        if (visible && !pending) {
          pending = setTimeout(() => {
            enqueue({ impressionId, renderedPosition, slot });
            observer.disconnect();
          }, VISIBLE_MS);
        } else if (!visible && pending) {
          clearTimeout(pending);
          pending = null;
        }
      },
      { threshold: [0, VISIBLE_SHARE] },
    );
    observer.observe(element);
    return () => {
      observer.disconnect();
      if (pending) clearTimeout(pending);
    };
  }, [ref, impressionId, renderedPosition, slot]);
}

/** Reports every slot of a page shown whole, like a page of the Tribune,
 * once it has been open for a second. */
export function useViewReportsOnShow(views: ViewReport[]): void {
  const key = views.map((view) => view.impressionId).join(",");
  useEffect(() => {
    if (views.length === 0) return;
    const pending = setTimeout(() => views.forEach(enqueue), VISIBLE_MS);
    return () => clearTimeout(pending);
    // `key` stands for `views`: a new array with the same impressions is
    // the same page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
