import "server-only";

import { cookies } from "next/headers";

import { BROWSING_SESSION_COOKIE } from "@/lib/browsingSession";

/**
 * Set by a reader's choice on ConsentBanner (or the Settings toggle), never
 * by middleware.ts - unlike jn_sid, this cookie represents a decision, not a
 * default. middleware.ts reads its raw string value directly via
 * `request.cookies.get(CONSENT_COOKIE)` rather than importing anything from
 * this file beyond the constant: `cookies()` from next/headers only works
 * inside a route segment's request context, which middleware does not run
 * in (see BROWSING_SESSION_COOKIE in lib/browsingSession.ts for the same
 * split, already established there).
 */
export const CONSENT_COOKIE = "jn_consent";

export type ConsentState = "granted" | "denied";

function isConsentState(value: string | undefined): value is ConsentState {
  return value === "granted" || value === "denied";
}

/** `null` means undecided - the reader has not been asked yet, or the
 * cookie expired. Distinct from `"denied"`, which is an answer. */
export async function getConsentState(): Promise<ConsentState | null> {
  const store = await cookies();
  const value = store.get(CONSENT_COOKIE)?.value;
  return isConsentState(value) ? value : null;
}

/**
 * The only place `jn_consent` is written - see setConsentAction (the
 * Settings toggle) and app/api/consent/route.ts (the banner) for why each
 * caller exists. Sets or deletes jn_sid in the same response, so a grant or
 * a withdrawal takes effect immediately rather than on some later request.
 */
export async function writeConsent(state: ConsentState): Promise<void> {
  const store = await cookies();
  store.set(CONSENT_COOKIE, state, {
    maxAge: 60 * 60 * 24 * 180,
    sameSite: "lax",
    httpOnly: true,
    path: "/",
  });
  if (state === "granted") {
    const existing = store.get(BROWSING_SESSION_COOKIE)?.value;
    store.set(BROWSING_SESSION_COOKIE, existing ?? crypto.randomUUID(), {
      maxAge: 60 * 60 * 24 * 30,
      sameSite: "lax",
      path: "/",
    });
  } else {
    store.delete(BROWSING_SESSION_COOKIE);
  }
}

/** One universal opt-in gate - GDPR's model, applied to everyone regardless
 * of jurisdiction, per CLAUDE.md's "strictest applicable regime is the
 * design target." Only "granted" unlocks analytics; "denied" and undecided
 * both fail closed. */
export async function hasAnalyticsConsent(): Promise<boolean> {
  return (await getConsentState()) === "granted";
}
