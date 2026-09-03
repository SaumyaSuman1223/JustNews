import { type NextRequest, NextResponse } from "next/server";
import { type CookieOptions, createServerClient } from "@supabase/ssr";

import { BROWSING_SESSION_COOKIE } from "@/lib/browsingSession";
import { SUPABASE_ANON_KEY, SUPABASE_URL, isSupabaseConfigured } from "@/lib/supabase/config";

/**
 * Refreshes the Supabase session cookie on every request, and ensures every
 * visitor - signed in or not - carries a stable browsing-session id.
 *
 * The Supabase refresh matters because access tokens expire; without it, a
 * Server Component's read-only cookie access (`lib/supabase/server.ts`) can
 * never write the refreshed token back, and a long-lived tab quietly signs
 * itself out. This is the one place in the request lifecycle that both reads
 * and writes cookies, which is why Supabase's own guidance puts session
 * refresh here and nowhere else.
 *
 * The session id is unrelated to identity - it groups one browsing session's
 * impressions and interactions together (`session_id` on every interaction
 * log row) so they read as one session even across a sign-in, which matters
 * for the Stage 7 exploration deck's cold-start signal.
 *
 * It also forwards the request's own path and query string as headers, which
 * is the only way a Server Component can read them: `next/navigation`'s
 * `usePathname` is client-only, and the locale-segmented layout that needs
 * this - so the language switcher can link to the page the reader is
 * actually on, rather than always dropping them at the home page - renders
 * on the server.
 */
export async function middleware(request: NextRequest) {
  // Resolved before `response` exists, and re-applied to it below - the
  // Supabase cookie handler below reassigns `response` to a fresh object,
  // which would otherwise silently drop this cookie.
  const sessionId = request.cookies.get(BROWSING_SESSION_COOKIE)?.value ?? crypto.randomUUID();
  request.cookies.set(BROWSING_SESSION_COOKIE, sessionId);

  /**
   * Rebuilds `NextResponse.next({ request })` with two extra request headers.
   * A fresh `Headers` clone taken at the call site, not a snapshot held
   * across the function: `request.cookies.set` mutates `request`'s own
   * headers in place, and this runs after every such mutation below (once
   * here, and again inside the Supabase cookie handler once it has written
   * any refreshed auth cookies), so each clone picks up whatever is current
   * at that point - the same guarantee `NextResponse.next({ request })`
   * already gave the cookie flow, just carried over to these two headers.
   */
  function nextWithPathname() {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-pathname", request.nextUrl.pathname);
    requestHeaders.set("x-search", request.nextUrl.search);
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  let response = nextWithPathname();

  if (isSupabaseConfigured) {
    const supabase = createServerClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          response = nextWithPathname();
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    });

    // The call itself is what triggers a refresh when the token is stale -
    // the return value is unused here, only the cookie side effect matters.
    await supabase.auth.getUser();
  }

  response.cookies.set(BROWSING_SESSION_COOKIE, sessionId, {
    maxAge: 60 * 60 * 24 * 30,
    sameSite: "lax",
  });
  return response;
}

export const config = {
  matcher: [
    // Every route except static assets and image optimisation output.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|webp|avif|ico)$).*)",
  ],
};
