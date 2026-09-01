import "server-only";

import { cookies } from "next/headers";
import { type CookieOptions, createServerClient } from "@supabase/ssr";

import { SUPABASE_ANON_KEY, SUPABASE_URL, isSupabaseConfigured } from "./config";

/**
 * For Server Components and Route Handlers.
 *
 * Cookie writes here are wrapped in a try/catch: a Server Component cannot
 * set cookies at all, only read them - only `middleware.ts` can write, which
 * is what actually keeps a session refreshed across requests. Calling this
 * from a Server Component still works for reads; the catch just accepts that
 * a write attempt there is a no-op rather than an unhandled crash.
 */
export async function createServerSupabaseClient() {
  if (!isSupabaseConfigured) {
    throw new Error("Supabase is not configured - set NEXT_PUBLIC_SUPABASE_URL and _ANON_KEY.");
  }
  const cookieStore = await cookies();
  return createServerClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Called from a Server Component - middleware.ts refreshes instead.
        }
      },
    },
  });
}
