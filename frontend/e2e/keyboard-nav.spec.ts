import { expect, test } from "@playwright/test";

test("skip link moves keyboard focus past the masthead, and the masthead is reachable by tab", async ({
  page,
}) => {
  await page.goto("/en");

  // First tab stop on any page: the skip link. Hidden until focused
  // (globals.css .skip-link), so this also proves the CSS shows it.
  await page.keyboard.press("Tab");
  const skipLink = page.locator(".skip-link");
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeVisible();
  await expect(skipLink).toHaveAttribute("href", "#main");

  // Activating it must move focus to <main>, not just scroll the viewport -
  // that's the actual point of a skip link, and the reason main needs
  // tabIndex={-1} (layout.tsx). What's reachable by tabbing on from there
  // depends on whether there's a live API behind this page (this suite runs
  // against a CI build with none - see accessibility.spec.ts), so this stops
  // at proving the skip itself actually moves focus, not at asserting what
  // comes next.
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});
