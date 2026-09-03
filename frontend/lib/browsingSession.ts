import "server-only";

import { cookies } from "next/headers";

/** Set by middleware.ts on every visitor's first request. */
export const BROWSING_SESSION_COOKIE = "jn_sid";

/**
 * Groups one browsing session's impressions and interactions together,
 * independent of identity. `null` when the reader has not granted analytics
 * consent (lib/consent.ts) - middleware.ts only mints and forwards this
 * cookie once `jn_consent=granted`, so its absence here is not a bug to work
 * around with a fallback value, it is consent working as designed.
 */
export async function getBrowsingSessionId(): Promise<string | null> {
  const store = await cookies();
  return store.get(BROWSING_SESSION_COOKIE)?.value ?? null;
}
