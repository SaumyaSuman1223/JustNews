import "server-only";

import { cache } from "react";

import { isSupabaseConfigured } from "@/lib/supabase/config";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export interface Session {
  userId: string;
  email: string | null;
  /** Forwarded as the API's bearer token - the API verifies it itself. */
  accessToken: string;
}

/**
 * The signed-in reader, or `null` for anonymous - never throws. Every route
 * that needs auth checks this and degrades to a sign-in prompt rather than
 * assuming a session exists.
 *
 * `getUser()`, not a cookie-decoded session, is what actually asks Supabase's
 * auth server to validate the token - trusting the cookie's claims directly
 * would trust whatever a client sent.
 */
/**
 * Once per request, however many layouts and pages ask. `getUser()` is a
 * network round trip to Supabase Auth, and the shell, the page and the feed
 * body each used to make their own - three serial hops before a signed-in
 * page could render (docs/decisions/0014).
 */
export const getSession = cache(async function getSession(): Promise<Session | null> {
  if (!isSupabaseConfigured) return null;
  try {
    const supabase = await createServerSupabaseClient();
    const { data: userData, error: userError } = await supabase.auth.getUser();
    if (userError || !userData.user) return null;
    const { data: sessionData } = await supabase.auth.getSession();
    const accessToken = sessionData.session?.access_token;
    if (!accessToken) return null;
    return { userId: userData.user.id, email: userData.user.email ?? null, accessToken };
  } catch {
    return null;
  }
});
