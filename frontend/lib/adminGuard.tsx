import Link from "next/link";
import type { ReactElement } from "react";

import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getSession } from "@/lib/session";

export interface AuthContext {
  accessToken: string;
  /** `null` pre-consent - see lib/consent.ts and getBrowsingSessionId. */
  sessionId: string | null;
}

export type AdminAccessResult = { ok: true; auth: AuthContext } | { ok: false; element: ReactElement };

export async function requireAdmin(): Promise<AdminAccessResult> {
  const session = await getSession();
  if (!session) {
    return {
      ok: false,
      element: (
        <p className="empty">
          Sign in with an admin account. <Link href="/en/login?next=/admin">Sign in</Link>
        </p>
      ),
    };
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const profile = await getMe(auth);
  if (profile?.role !== "admin") {
    return { ok: false, element: <p className="empty">This account does not have admin access.</p> };
  }
  return { ok: true, auth };
}
