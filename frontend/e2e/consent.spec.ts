import { expect, test } from "@playwright/test";

/**
 * The banner is server-rendered and both its buttons are plain
 * `<form action={...}>` submissions - no client JS to wait on beyond
 * Playwright's own navigation handling, matching how the rest of this app's
 * one-shot actions already work.
 */
test.describe("consent", () => {
  test("no browsing-session cookie exists before a choice is made", async ({ page, context }) => {
    await page.goto("/en");
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name === "jn_sid")).toBeUndefined();
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeVisible();
  });

  test("accepting grants a browsing-session cookie and dismisses the banner", async ({
    page,
    context,
  }) => {
    await page.goto("/en");
    await page.getByRole("button", { name: "Accept" }).click();
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeHidden();
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name === "jn_sid")).toBeDefined();
    expect(cookies.find((c) => c.name === "jn_consent")?.value).toBe("granted");
  });

  test("declining dismisses the banner without a browsing-session cookie", async ({
    page,
    context,
  }) => {
    await page.goto("/en");
    await page.getByRole("button", { name: "Decline" }).click();
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeHidden();
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name === "jn_sid")).toBeUndefined();
    expect(cookies.find((c) => c.name === "jn_consent")?.value).toBe("denied");
  });
});
