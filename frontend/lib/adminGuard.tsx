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

export type AdminAccessResult =
  { ok: true; auth: AuthContext } | { ok: false; element: ReactElement };

export async function requireAdmin(): Promise<AdminAccessResult> {
  const session = await getSession();
  if (!session) {
    return {
      ok: false,
      element: (
        <div className="empty">
          <h1 className="empty__title">Admin</h1>
          <p>
            Sign in with an admin account. <Link href="/en/login?next=/admin">Sign in</Link>
          </p>
        </div>
      ),
    };
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const profile = await getMe(auth);
  if (profile?.role !== "admin") {
    return {
      ok: false,
      element: (
        <div className="empty">
          <h1 className="empty__title">Admin</h1>
          <p>This account does not have admin access.</p>
        </div>
      ),
    };
  }
  return { ok: true, auth };
}
