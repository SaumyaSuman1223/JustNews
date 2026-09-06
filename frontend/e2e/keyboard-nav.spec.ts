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

/**
 * The icon rail's failure mode (audit §14).
 *
 * An icon rail is easy to build and easy to build wrongly: the label becomes a
 * hover tooltip, the tooltip is hidden with `display: none` or `visibility`,
 * and the destination is then an unnamed link for anyone not using a mouse.
 * These assertions are specifically about the name surviving - by role and
 * name, which is what a screen reader would use, not by CSS.
 */
test("the icon rail is keyboard-reachable and every destination keeps a name", async ({ page }) => {
  // Above the 900px line, where the rail replaces the mobile tab bar.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/en");

  const rail = page.locator(".rail-nav");
  await expect(rail).toBeVisible();
  // 52-60px, per §14. The measurement is the point of the chunk.
  const box = await page.locator(".masthead").boundingBox();
  expect(box?.width).toBeGreaterThanOrEqual(52);
  expect(box?.width).toBeLessThanOrEqual(60);

  const home = rail.getByRole("link", { name: "Home", exact: true });
  await expect(home).toHaveAttribute("aria-current", "page");

  // At rest the label is transparent, not removed - `toBeVisible` is true
  // because opacity is not visibility, which is exactly the property that
  // keeps it in the accessibility tree.
  const label = home.locator(".rail-link__label");
  await expect(label).toHaveCSS("opacity", "0");

  // Tabbed to, not `.focus()`d: the reveal is on `:focus-visible`, and only a
  // real keyboard interaction sets it. Skip link, wordmark, then the rail.
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(home).toBeFocused();
  await expect(label).toHaveCSS("opacity", "1");
});
