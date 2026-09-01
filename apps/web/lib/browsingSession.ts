import "server-only";

import { cookies } from "next/headers";

/** Set by middleware.ts on every visitor's first request. */
export const BROWSING_SESSION_COOKIE = "jn_sid";

/**
 * Groups one browsing session's impressions and interactions together,
 * independent of identity - middleware.ts guarantees this cookie exists
 * before any Server Component or Server Action runs.
 */
export async function getBrowsingSessionId(): Promise<string> {
  const store = await cookies();
  return store.get(BROWSING_SESSION_COOKIE)?.value ?? "unknown";
}
