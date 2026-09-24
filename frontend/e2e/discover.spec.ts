import { expect, test } from "@playwright/test";

/**
 * Discover's rail. "Make it yours" is the first thing a new reader is asked
 * - and asked once: answering it, either way, is remembered.
 */
test.describe("discover rail", () => {
  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      { name: "jn_consent", value: "denied", domain: "127.0.0.1", path: "/" },
    ]);
  });

  test("choosing interests saves them and stops asking", async ({ page, context }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/en");
    const card = page.getByRole("region", { name: "Make it yours" });
    await expect(card).toBeVisible();
    const save = card.getByRole("button", { name: "Save interests" });
    await expect(save).toBeDisabled();

    await card.getByRole("button", { name: "Politics" }).click();
    await expect(card.getByRole("button", { name: "Politics" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await save.click();
    await expect(card).toBeHidden();
    await expect
      .poll(async () => {
        const value = (await context.cookies()).find((c) => c.name === "jn_interests")?.value;
        return value && decodeURIComponent(value);
      })
      .toBe("medtop:11000000");

    await page.reload();
    await expect(page.getByRole("region", { name: "Make it yours" })).toBeHidden();
  });

  test("closing the card is remembered too", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/en");
    const card = page.getByRole("region", { name: "Make it yours" });
    await Promise.all([
      page.waitForResponse((response) => response.url().endsWith("/api/interests")),
      card.getByRole("button", { name: "Not now" }).click(),
    ]);
    await expect(card).toBeHidden();
    await page.reload();
    await expect(page.getByRole("region", { name: "Make it yours" })).toBeHidden();
  });

  test("a widget can be hidden from the customize panel", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/en");
    const rail = page.getByRole("complementary", { name: "Your Discover rail" });
    await expect(rail.getByRole("heading", { name: "Weather" })).toBeVisible();

    await page.getByRole("button", { name: "Customize" }).first().click();
    await rail.getByRole("checkbox", { name: "Weather" }).uncheck();
    await expect(rail.getByRole("heading", { name: "Weather", exact: true })).toBeHidden();

    await page.reload();
    await expect(
      page
        .getByRole("complementary", { name: "Your Discover rail" })
        .getByRole("heading", { name: "Weather", exact: true }),
    ).toBeHidden();
  });
});

test.describe("discover", () => {
  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      { name: "jn_consent", value: "denied", domain: "127.0.0.1", path: "/" },
    ]);
  });

  // The server once kept Discover's view cache between requests, so the page
  // rendered for one language carried the stories of the one before it and
  // React threw the server's HTML away (#418).
  test("each language's page hydrates cleanly after another's", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    for (const locale of ["en", "es", "hi", "en"]) {
      await page.goto(`/${locale}`);
      await page.waitForLoadState("networkidle");
    }
    expect(errors).toEqual([]);
  });

  test("For You says it is showing Top until interests are chosen", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/en");
    const card = page.getByRole("region", { name: "Make it yours" });
    await card.getByRole("button", { name: "Not now" }).click();
    const note = page.getByText("For You shows Top stories until you choose some interests.");
    await expect(note).toBeVisible();

    await page.getByRole("button", { name: "Choose interests" }).click();
    await expect(card).toBeVisible();
    await expect(card.getByRole("heading", { name: "Make it yours" })).toBeFocused();
    await expect(note).toBeHidden();
  });
});

test.describe("phone drawer", () => {
  test("moves focus in, keeps the page out of reach, and returns focus", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/en");
    const menu = page.getByRole("button", { name: "Open menu" });
    await menu.click();
    await expect(page.locator("#sidebar :focus")).toHaveCount(1);
    await expect(page.locator("#main")).toHaveAttribute("inert", "");

    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open menu" })).toBeFocused();
    await expect(page.locator("#main")).not.toHaveAttribute("inert", "");
  });
});
