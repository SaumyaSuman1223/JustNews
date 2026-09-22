import { useSyncExternalStore } from "react";

const LAST_VISIT_KEY = "jn_last_visit";
const PREVIOUS_KEY = "jn_previous_visit";

let previous: number | null | undefined;

/**
 * When this reader last opened JustNews in this browser, before the visit
 * they are on now - or null on a first visit.
 *
 * Kept on the device only (localStorage, like recent searches): it never
 * reaches the server, so it is not tracking - it is the page remembering
 * where the reader left off. Pinned for the whole tab session in
 * sessionStorage, so paging through Home or coming back from an article
 * does not reset what counts as "new".
 */
function readPrevious(): number | null {
  if (previous !== undefined) return previous;
  try {
    const pinned = window.sessionStorage.getItem(PREVIOUS_KEY);
    if (pinned !== null) {
      previous = pinned === "" ? null : Number(pinned);
    } else {
      const stored = window.localStorage.getItem(LAST_VISIT_KEY);
      previous = stored ? Number(stored) : null;
      window.sessionStorage.setItem(PREVIOUS_KEY, stored ?? "");
    }
    window.localStorage.setItem(LAST_VISIT_KEY, String(Date.now()));
  } catch {
    // Storage refused (private window). "New" is a convenience; without it
    // nothing is marked, which is the same as a first visit.
    previous = null;
  }
  return previous;
}

const subscribe = () => () => {};

/** See `readPrevious`. Null on the server and during hydration, so the
 * server's HTML never claims to know what this reader has seen. */
export function usePreviousVisit(): number | null {
  return useSyncExternalStore(subscribe, readPrevious, () => null);
}
