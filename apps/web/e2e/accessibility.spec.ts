import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Public, unauthenticated routes only - the CI environment this runs in has
 * no live API behind it (see ci.yml's `web` job), so a dynamic article/story
 * page would just be its own 404, not the real thing. These four are the
 * routes that render meaningfully - degraded, but validly - without one:
 * the feed's empty state, the topics list, search, and the sign-in form.
 * `ar` is the RTL canary - if logical CSS properties are wrong anywhere,
 * this is where an axe rule or a visual mirror bug would show up.
 */
const ROUTES = ["/en", "/ar", "/en/topics", "/en/search", "/en/login"];

for (const route of ROUTES) {
  test(`${route} has no axe violations`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
