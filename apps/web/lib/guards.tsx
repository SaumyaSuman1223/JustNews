import type { ReactElement } from "react";

import { BetaGateNotice } from "@/components/BetaGateNotice";
import { SignInRequired } from "@/components/SignInRequired";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getSession } from "@/lib/session";

export interface AuthContext {
  accessToken: string;
  sessionId: string;
}

export type BetaAccessResult = { ok: true; auth: AuthContext } | { ok: false; element: ReactElement };

/**
 * The gate every page behind ``/v1/feed``, ``/v1/saves``, ``/v1/follows`` or
 * ``/v1/history`` needs: signed in, *and* invite-redeemed. Two different
 * reasons to fail, two different prompts - "sign in" is not "you need an
 * invite", and conflating them would send an already-signed-in reader back
 * through a login form that cannot fix their actual problem.
 */
export async function requireBetaAccess(locale: string, path: string): Promise<BetaAccessResult> {
  const session = await getSession();
  if (!session) {
    return { ok: false, element: <SignInRequired locale={locale} path={path} /> };
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const profile = await getMe(auth);
  if (!profile?.has_beta_access) {
    return { ok: false, element: <BetaGateNotice locale={locale} /> };
  }
  return { ok: true, auth };
}
