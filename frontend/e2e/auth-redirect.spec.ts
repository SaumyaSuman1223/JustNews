import { expect, test } from "@playwright/test";

/**
 * `next=` decides where someone lands the moment they are authenticated, and
 * it comes from the URL - in the callback's case, from a link in an email.
 * Taken as given it was an open redirect: a real sign-in page that handed off
 * to whatever site the link author chose, which is the exact shape a
 * credential-phishing page needs.
 *
 * Driven through /auth/callback rather than the sign-in form because the form
 * needs Supabase configured and CI has no credentials, while this route
 * redirects without them - and both call the same `safeNext`.
 */
const CASES: { name: string; next: string; lands: string }[] = [
  { name: "an absolute URL elsewhere", next: "https://example.org/phish", lands: "/en" },
  { name: "a protocol-relative host", next: "//example.org", lands: "/en" },
  { name: "a backslash-escaped host", next: "/\\example.org", lands: "/en" },
  { name: "a legitimate in-app path", next: "/en/saved", lands: "/en/saved" },
];

for (const { name, next, lands } of CASES) {
  test(`auth callback with ${name} lands on ${lands}`, async ({ request }) => {
    const response = await request.get(`/auth/callback?next=${encodeURIComponent(next)}`, {
      maxRedirects: 0,
    });
    expect(response.status()).toBe(307);
    const location = response.headers()["location"] ?? "";
    expect(location, "the callback must always send a Location header").not.toBe("");
    expect(new URL(location).pathname).toBe(lands);
  });
}
