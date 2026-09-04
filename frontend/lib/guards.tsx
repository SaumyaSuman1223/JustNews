import type { ReactElement } from "react";

import { BetaGateNotice } from "@/components/BetaGateNotice";
import { SignInRequired } from "@/components/SignInRequired";
import { getMe, type MeProfile } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import type { LocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export interface AuthContext {
  accessToken: string;
  /** `null` pre-consent - see lib/consent.ts and getBrowsingSessionId. */
  sessionId: string | null;
}

export type BetaAccessResult =
  // The profile comes back with the pass because the gate has already paid
  // for it, and every gated page needs `preferred_languages` off it. Fetching
  // it twice would be a second transcontinental round trip for a value we are
  // holding.
  | { ok: true; auth: AuthContext; profile: MeProfile }
  | { ok: false; element: ReactElement };

/**
 * The gate every page behind ``/v1/feed``, ``/v1/saves``, ``/v1/follows`` or
 * ``/v1/history`` needs: signed in, *and* invite-redeemed. Two different
 * reasons to fail, two different prompts - "sign in" is not "you need an
 * invite", and conflating them would send an already-signed-in reader back
 * through a login form that cannot fix their actual problem.
 */
export async function requireBetaAccess(
  locale: LocaleCode,
  path: string,
): Promise<BetaAccessResult> {
  const session = await getSession();
  if (!session) {
    return { ok: false, element: <SignInRequired locale={locale} path={path} /> };
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const profile = await getMe(auth);
  if (!profile?.has_beta_access) {
    return { ok: false, element: <BetaGateNotice locale={locale} /> };
  }
  return { ok: true, auth, profile };
}
