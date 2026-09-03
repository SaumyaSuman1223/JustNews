/**
 * Sanitises a `next=` redirect target.
 *
 * Both sign-in paths take where-to-go-afterwards from the query string, and
 * both used it as given. `/en/login?next=https://example.org/phish` therefore
 * sent the reader straight off-site the moment their credentials were
 * accepted - the classic phishing shape, where a genuine sign-in page hands
 * off to a lookalike that asks them to "sign in again".
 *
 * Only a same-origin absolute path is allowed through. Everything else falls
 * back rather than throwing: a bad `next` is not a reason to deny someone a
 * session they have legitimately established.
 */
export function safeNext(next: string | null | undefined, fallback: string): string {
  if (!next) return fallback;

  // Must be an absolute path on this origin. A second leading slash (or a
  // backslash, which several browsers normalise to one) makes it
  // protocol-relative - `//example.org` is a host, not a path.
  if (!next.startsWith("/")) return fallback;
  if (next.startsWith("//") || next.startsWith("/\\")) return fallback;

  // Control characters, including the tab/newline that browsers strip out of
  // URLs before parsing them - `/\tjavascript:...` and `/\n/example.org` both
  // survive the checks above and are re-read as something else afterwards.
  if (/[\u0000-\u001f\u007f]/.test(next)) return fallback;

  return next;
}
