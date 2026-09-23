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
