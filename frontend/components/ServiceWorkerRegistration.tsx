"use client";

import { useEffect } from "react";

/**
 * Registered in production only - a service worker fighting Fast Refresh's
 * own caching in dev is a well-known footgun, with nothing to gain locally.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Best-effort: a reader who can't get a service worker still gets the
      // site, just without offline saves.
    });
  }, []);

  return null;
}
