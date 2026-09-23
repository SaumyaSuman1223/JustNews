import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * False while the server renders and while the client hydrates; true on
 * every render after.
 *
 * For text that depends on the reader's clock or timezone - "23 minutes
 * ago", an edition time in local hours. The server cannot know either, so
 * the first client render must reuse the server's text (the element carries
 * `suppressHydrationWarning`, which keeps that text rather than failing
 * hydration). Reading this hook is what then makes React re-render the
 * component straight after hydration, with the real local values - one
 * update, instead of the whole tree being discarded and re-rendered from
 * scratch, which is what a mismatch did on every minute boundary (fifth
 * pass §2.3).
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
