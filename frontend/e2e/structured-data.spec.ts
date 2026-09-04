import { expect, test } from "@playwright/test";

/**
 * Required-field check, not schema validation - there is no public API for
 * Google's Rich Results Test, and claiming this proves more would overclaim
 * (CLAUDE.md's honesty rule). It confirms the JSON-LD block on an article
 * page parses and carries the fields a NewsArticle needs.
 *
 * Runs under playwright.structured-data.config.ts, the one place in this
 * suite with a live API behind it (a stub, scripts/stub-api.mjs) - every
 * other e2e test runs with none, deliberately (accessibility.spec.ts).
 */
test("an article page's JSON-LD parses and has the required NewsArticle fields", async ({
  page,
}) => {
  await page.goto("/en/a/1");

  const raw = await page.locator('script[type="application/ld+json"]').textContent();
  expect(raw).toBeTruthy();

  const jsonLd = JSON.parse(raw ?? "{}");
  expect(jsonLd["@type"]).toBe("NewsArticle");
  expect(typeof jsonLd.headline).toBe("string");
  expect(jsonLd.headline.length).toBeGreaterThan(0);
  expect(() => new Date(jsonLd.datePublished).toISOString()).not.toThrow();
  expect(jsonLd.inLanguage).toBe("en");
});
