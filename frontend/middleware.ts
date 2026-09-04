import { type NextRequest, NextResponse } from "next/server";
import { type CookieOptions, createServerClient } from "@supabase/ssr";

import { BROWSING_SESSION_COOKIE } from "@/lib/browsingSession";
import { CONSENT_COOKIE } from "@/lib/consent";
import { SUPABASE_ANON_KEY, SUPABASE_URL, isSupabaseConfigured } from "@/lib/supabase/config";

/**
 * Refreshes the Supabase session cookie on every request, and - once, and
 * only once, the reader has actually granted analytics consent - ensures
 * they carry a stable browsing-session id.
 *
 * The Supabase refresh matters because access tokens expire; without it, a
 * Server Component's read-only cookie access (`lib/supabase/server.ts`) can
 * never write the refreshed token back, and a long-lived tab quietly signs
 * itself out. This is the one place in the request lifecycle that both reads
 * and writes cookies, which is why Supabase's own guidance puts session
 * refresh here and nowhere else. It is unaffected by consent: an auth
 * cookie is necessary for the service to function at all, not the kind of
 * tracking consent law targets.
 *
 * The browsing-session id is unrelated to identity - it groups one browsing
 * session's impressions and interactions together (`session_id` on every
 * interaction log row) so they read as one session even across a sign-in,
 * which matters for the Stage 7 exploration deck's cold-start signal. That
 * is exactly the kind of observation GDPR's consent requirement covers, so
 * it does not exist until `jn_consent=granted` - see lib/consent.ts.
 *
 * Actively *deleted* only on an explicit "denied", never on "undecided" -
 * this matters on the exact request that grants consent for the first
 * time. setConsentAction (lib/actions.ts) sets jn_consent and mints jn_sid
 * together, synchronously, in that same request/response cycle; middleware
 * runs first and, on that request, still sees the *incoming* jn_consent as
 * undecided (it is what the request is in the process of setting) - if this
 * treated undecided the same as denied, it would delete the jn_sid the
 * action is about to create, and the two Set-Cookie headers race with
 * unspecified precedence. Undecided means "nothing to do" here; only a real
 * decision to opt out actively tears anything down.
 *
 * It also forwards the request's own path and query string as headers, which
 * is the only way a Server Component can read them: `next/navigation`'s
 * `usePathname` is client-only, and the locale-segmented layout that needs
 * this - so the language switcher can link to the page the reader is
 * actually on, rather than always dropping them at the home page - renders
 * on the server. Unaffected by consent - it is routing information, not
 * tracking.
 */
export async function middleware(request: NextRequest) {
  const consent = request.cookies.get(CONSENT_COOKIE)?.value;
  const consentGranted = consent === "granted";
  const consentDenied = consent === "denied";
  // Resolved before `response` exists, and re-applied to it below - the
  // Supabase cookie handler below reassigns `response` to a fresh object,
  // which would otherwise silently drop this cookie. `null` when consent is
  // denied or genuinely absent (no jn_sid exists to carry forward and none
  // is minted); `undefined` on an undecided request leaves whatever the
  // request already had untouched - see the doc comment above.
  const sessionId = consentGranted
    ? (request.cookies.get(BROWSING_SESSION_COOKIE)?.value ?? crypto.randomUUID())
    : consentDenied
      ? null
      : undefined;
  if (sessionId) {
    request.cookies.set(BROWSING_SESSION_COOKIE, sessionId);
  } else if (sessionId === null) {
    request.cookies.delete(BROWSING_SESSION_COOKIE);
  }

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

  if (sessionId) {
    response.cookies.set(BROWSING_SESSION_COOKIE, sessionId, {
      maxAge: 60 * 60 * 24 * 30,
      sameSite: "lax",
    });
  } else if (sessionId === null) {
    response.cookies.delete(BROWSING_SESSION_COOKIE);
  }
  return response;
}

export const config = {
  matcher: [
    // Every route except static assets and image optimisation output.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|webp|avif|ico)$).*)",
  ],
};
