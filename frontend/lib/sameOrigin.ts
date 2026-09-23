/**
 * Whether a state-changing request came from this site. Server Actions check
 * this themselves; a route handler that writes on the reader's behalf has to,
 * or any other page could post to it with the reader's cookies attached.
 *
 * Compared by host, not by `request.url`: behind Vercel's proxy (and in
 * `next start`) the URL a handler sees is not always the name the reader
 * used. A request with no Origin at all is a same-origin navigation or a
 * non-browser client, neither of which carries someone else's intent.
 */
export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (origin === null) return true;
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}
