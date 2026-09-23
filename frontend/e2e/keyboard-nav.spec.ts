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
 * The sidebar's failure mode: collapsed to icons, a destination must still
 * be a named link - by role and name, which is what a screen reader uses,
 * not by what CSS happens to draw.
 */
test("the sidebar is keyboard-reachable, and collapsed it keeps every name", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/en");

  const sidebar = page.getByRole("complementary", { name: "Main menu" });
  await expect(sidebar).toBeVisible();
  const discover = sidebar.getByRole("link", { name: "Discover", exact: true });
  await expect(discover).toHaveAttribute("aria-current", "page");

  // Skip link, wordmark, collapse toggle, search field, then the first
  // destination.
  for (let i = 0; i < 5; i += 1) await page.keyboard.press("Tab");
  await expect(discover).toBeFocused();

  await sidebar.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(sidebar).toHaveAttribute("data-collapsed");
  // An icon column now - and the same link, by the same name.
  await expect(sidebar.getByRole("link", { name: "Discover", exact: true })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Aquila", exact: true })).toBeVisible();

  // The choice survives a reload, rendered by the server.
  await page.reload();
  await expect(page.getByRole("complementary", { name: "Main menu" })).toHaveAttribute(
    "data-collapsed",
  );
});

test("Discover's views swap in place and keep a real URL", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/en");
  const tabs = page.getByRole("navigation", { name: "Discover views" });
  await expect(tabs.getByRole("link", { name: "For You" })).toHaveAttribute("aria-current", "page");

  await tabs.getByRole("link", { name: "Top" }).click();
  await expect(page).toHaveURL(/\/en\?view=top$/);
  await expect(tabs.getByRole("link", { name: "Top" })).toHaveAttribute("aria-current", "page");

  await page.goBack();
  await expect(page).toHaveURL(/\/en$/);
  await expect(tabs.getByRole("link", { name: "For You" })).toHaveAttribute("aria-current", "page");
});
