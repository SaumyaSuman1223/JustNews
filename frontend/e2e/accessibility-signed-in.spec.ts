import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * The signed-in surfaces axe never reaches.
 *
 * accessibility.spec.ts is deliberately public-only: CI has no Supabase
 * credentials, so `getSession()` (lib/session.ts) returns `null`
 * unconditionally and no signed-in page can render there at all - not via a
 * form, not via a cookie, nothing short of a real Supabase project issuing a
 * real token. That gap is exactly how the account menu's fake `role="menu"`
 * (fixed in 14bb75d) survived Stage 3's "fully usable with the keyboard
 * alone" sign-off: the one interactive, ARIA-bearing control behind sign-in
 * had zero coverage.
 *
 * This suite closes that gap the honest way rather than faking it. It signs
 * in for real, through Supabase's own password-grant endpoint, using a
 * dedicated test account - not the app's login form, so a slow or flaky UI
 * interaction isn't part of what this is testing. It then sets the session
 * cookie in the exact shape @supabase/ssr's server client expects
 * (`sb-<project-ref>-auth-token`, base64url-encoded, chunked past ~3180
 * chars - see node_modules/@supabase/ssr/dist/module/{cookies,utils/chunker}.js),
 * so the same server-side `getUser()` round trip every real request makes
 * validates it against Supabase, not a locally-decoded claim.
 *
 * It needs three things that do not exist in this repo yet:
 *   NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY - already read by
 *     the app itself, just not set anywhere in ci.yml's `web` job.
 *   E2E_TEST_EMAIL / E2E_TEST_PASSWORD - a real Supabase user made for this,
 *     with no beta access needed (the account menu renders the same either
 *     way; the invite item is the only thing that changes with it).
 * Missing any of them skips with a reason rather than failing red, matching
 * how every degraded path in this codebase behaves (ADR 0003) - a fully
 * absent capability is not the same failure as a broken one, and should not
 * read as one in CI.
 *
 * Activating this in CI is more than adding secrets, and is deliberately not
 * done here. `NEXT_PUBLIC_*` variables are inlined into the client bundle at
 * `next build`, not read at `next start` - so the `web` job's build step
 * would need them too, which makes `isSupabaseConfigured` true for every
 * other test in that job, not just this file. accessibility.spec.ts,
 * keyboard-nav.spec.ts and auth-redirect.spec.ts (its own comment says so
 * directly) are all written against Supabase being absent. Turning that on
 * is a real precondition change for the whole job and belongs in its own
 * reviewed change, alongside actually standing up a Supabase test project.
 */

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const TEST_EMAIL = process.env.E2E_TEST_EMAIL;
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;

const READY = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY && TEST_EMAIL && TEST_PASSWORD);

// @supabase/ssr's own chunk size (utils/chunker.js) - a cookie value longer
// than this splits across `<name>.0`, `<name>.1`, ... A typical session is
// short enough to stay in one chunk, but a test account with unusual custom
// claims should not silently drop data, so this still implements the split.
const COOKIE_CHUNK_SIZE = 3180;

interface SupabaseTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in: number;
  expires_at?: number;
  user: unknown;
}

function chunkCookieValue(name: string, value: string): { name: string; value: string }[] {
  // encodeURIComponent(value) === value here: the value is already base64url
  // (`[A-Za-z0-9_-]` only), which has nothing left to percent-encode, so the
  // library's own size check (measured post-encoding) and a plain
  // `.length` check agree.
  if (value.length <= COOKIE_CHUNK_SIZE) return [{ name, value }];
  const chunks: { name: string; value: string }[] = [];
  for (let i = 0; i * COOKIE_CHUNK_SIZE < value.length; i++) {
    chunks.push({
      name: `${name}.${i}`,
      value: value.slice(i * COOKIE_CHUNK_SIZE, (i + 1) * COOKIE_CHUNK_SIZE),
    });
  }
  return chunks;
}

/**
 * Signs in via Supabase's REST API and injects the resulting session as the
 * cookie `lib/supabase/server.ts` reads. Throws on a failed sign-in rather
 * than leaving the page to fail more confusingly later.
 */
async function signIn(page: Page): Promise<void> {
  const tokenUrl = `${SUPABASE_URL}/auth/v1/token?grant_type=password`;
  const response = await fetch(tokenUrl, {
    method: "POST",
    headers: { "content-type": "application/json", apikey: SUPABASE_ANON_KEY! },
    body: JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
  });
  if (!response.ok) {
    throw new Error(
      `E2E_TEST_EMAIL sign-in failed (${response.status}): ${await response.text()}`,
    );
  }
  const token = (await response.json()) as SupabaseTokenResponse;

  // The shape GoTrueClient persists is the token endpoint's response as-is -
  // access_token, refresh_token, the expiry pair and the user object - so
  // the REST response is passed straight through rather than reshaped.
  const session = {
    access_token: token.access_token,
    refresh_token: token.refresh_token,
    token_type: token.token_type ?? "bearer",
    expires_in: token.expires_in,
    expires_at: token.expires_at ?? Math.floor(Date.now() / 1000) + token.expires_in,
    user: token.user,
  };

  // sb-<project-ref>-auth-token: supabase-js derives the ref from the
  // project URL's hostname when no cookieOptions.name is given, and neither
  // lib/supabase/client.ts nor server.ts gives one.
  const projectRef = new URL(SUPABASE_URL!).hostname.split(".")[0];
  const cookieName = `sb-${projectRef}-auth-token`;
  const encoded = `base64-${Buffer.from(JSON.stringify(session)).toString("base64url")}`;

  await page.context().addCookies(
    chunkCookieValue(cookieName, encoded).map(({ name, value }) => ({
      name,
      value,
      url: "http://127.0.0.1:3000",
    })),
  );
}

test.describe("account menu, signed in", () => {
  test.skip(!READY, "needs NEXT_PUBLIC_SUPABASE_URL/_ANON_KEY and E2E_TEST_EMAIL/_PASSWORD");

  test.beforeEach(async ({ page }) => {
    await signIn(page);
    await page.goto("/en");
    // The trigger renders the reader's email once the server has resolved a
    // real session - proof the cookie was accepted, not just sent.
    await expect(page.locator(".account-menu__trigger")).toBeVisible();
  });

  test("open panel has no axe violations", async ({ page }) => {
    await page.locator(".account-menu__trigger").click();
    await expect(page.locator(".account-menu__panel")).toBeVisible();

    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });

  test("Escape closes the panel and returns focus to the trigger", async ({ page }) => {
    const trigger = page.locator(".account-menu__trigger");
    await trigger.click();
    await expect(page.locator(".account-menu__panel")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.locator(".account-menu__panel")).toBeHidden();
    await expect(trigger).toBeFocused();
  });

  test("a click outside the panel closes it", async ({ page }) => {
    await page.locator(".account-menu__trigger").click();
    await expect(page.locator(".account-menu__panel")).toBeVisible();

    await page.locator("main").click({ position: { x: 10, y: 10 } });
    await expect(page.locator(".account-menu__panel")).toBeHidden();
  });
});
