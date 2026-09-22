import { NextResponse } from "next/server";

import { type ConsentState, writeConsent } from "@/lib/consent";

/**
 * The consent banner's two buttons post here, and the reader lands back on
 * the page they were reading.
 *
 * A plain form post and a 303, not a Server Action. With the action, Next
 * applied the choice (the cookie was set) but on Home its re-render of the
 * layout never committed in a production build, so the banner stayed on
 * screen until the next navigation - reproduced on every build back to
 * before the fifth pass, and not in dev (fifth pass part 9). A full page
 * load after a once-per-browser choice costs little, works the same with
 * JavaScript off, and renders the next page with the new cookie from the
 * start.
 */
export async function POST(request: Request): Promise<Response> {
  // A consent grant is only the reader's if this site asked for it. Server
  // Actions check this themselves; a route handler has to, or any other site
  // could post a "granted" on the reader's behalf.
  const host = siteHost(request);
  const origin = request.headers.get("origin");
  if (origin !== null && hostOf(origin) !== host) {
    return NextResponse.json({ ok: false }, { status: 403 });
  }
  const form = await request.formData().catch(() => null);
  const choice = form?.get("choice");
  if (choice !== "granted" && choice !== "denied") {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  await writeConsent(choice satisfies ConsentState);
  // A relative Location, so the reader returns to the host they are on
  // rather than whatever name the server sees itself as behind a proxy.
  return new Response(null, { status: 303, headers: { Location: returnPath(request, host) } });
}

/** The host the reader addressed - the proxy's forwarded name on Vercel. */
function siteHost(request: Request): string | null {
  return request.headers.get("x-forwarded-host") ?? request.headers.get("host");
}

function hostOf(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

/**
 * Back to the page the banner was on, read from Referer - the layout that
 * renders the banner does not know the current path, and this site's
 * Referrer-Policy (strict-origin-when-cross-origin) sends the full URL on a
 * same-origin post. Only ever this site: a Referer naming another origin, or
 * none at all (a privacy extension strips it), lands on the root instead. An
 * unchecked return address is an open redirect.
 */
function returnPath(request: Request, host: string | null): string {
  const referer = request.headers.get("referer");
  if (referer && host !== null && hostOf(referer) === host) {
    const from = new URL(referer);
    return from.pathname + from.search;
  }
  return "/";
}
