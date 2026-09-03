import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export interface Session {
  userId: string;
  email: string | null;
  /** Forwarded as the API's bearer token - the API verifies it itself. */
  accessToken: string;
}

/**
 * frontend/lib/session.ts's `getSession()` is a per-request server call
 * against a cookie - there is no server and no cookie here. This is the RN
 * equivalent: one subscription, held for the app's lifetime, updated by the
 * SDK's own `onAuthStateChange` (which also fires after its automatic token
 * refresh) rather than re-read on every screen.
 */
const SessionContext = createContext<{ session: Session | null; loading: boolean }>({
  session: null,
  loading: true,
});

function toSession(
  user: { id: string; email?: string | null } | null | undefined,
  accessToken: string | null | undefined,
): Session | null {
  if (!user || !accessToken) return null;
  return { userId: user.id, email: user.email ?? null, accessToken };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      setSession(toSession(data.session?.user, data.session?.access_token));
      setLoading(false);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(toSession(next?.user, next?.access_token));
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  return <SessionContext.Provider value={{ session, loading }}>{children}</SessionContext.Provider>;
}

/**
 * The signed-in reader, or `null` for anonymous. `loading` is true only
 * until the very first session check resolves - screens should show their
 * own loading state until then, the same way frontend never renders a page
 * before `getSession()` has answered.
 */
export function useSession(): { session: Session | null; loading: boolean } {
  return useContext(SessionContext);
}
