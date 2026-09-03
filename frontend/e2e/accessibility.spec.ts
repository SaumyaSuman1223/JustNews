import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Public, unauthenticated routes only - the CI environment this runs in has
 * no live API behind it (see ci.yml's `web` job), so a dynamic article/story
 * page would just be its own 404, not the real thing. These are the routes
 * that render meaningfully - degraded, but validly - without one: the
 * feed's empty state, the topics list, search, the sign-in form, and privacy
 * (fully static, no API call at all). `hi` is the non-Latin canary -
 * Devanagari has taller ascenders and descenders than Latin, so clipped line
 * boxes and cramped leading show up there first; on /hi/privacy it also
 * exercises the translated "English only" notice specifically.
 */
const ROUTES = [
  "/en",
  "/hi",
  "/en/explore",
  "/en/topics",
  "/en/search",
  "/en/login",
  "/en/privacy",
  "/hi/privacy",
];

for (const route of ROUTES) {
  test(`${route} has no axe violations`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
