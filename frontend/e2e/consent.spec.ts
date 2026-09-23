import { expect, test } from "@playwright/test";

/**
 * The banner is server-rendered and both its buttons are plain form posts to
 * /api/consent, which answers with a 303 back to the page - so a choice is a
 * full page load, and the cookie checks poll rather than read once: the
 * banner can be gone (the page is unloading) a moment before the response
 * that sets the cookie has landed.
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
    await expect
      .poll(async () => (await context.cookies()).find((c) => c.name === "jn_consent")?.value)
      .toBe("granted");
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeHidden();
    expect((await context.cookies()).find((c) => c.name === "jn_sid")).toBeDefined();
  });

  test("declining dismisses the banner without a browsing-session cookie", async ({
    page,
    context,
  }) => {
    await page.goto("/en");
    await page.getByRole("button", { name: "Decline" }).click();
    await expect
      .poll(async () => (await context.cookies()).find((c) => c.name === "jn_consent")?.value)
      .toBe("denied");
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeHidden();
    expect((await context.cookies()).find((c) => c.name === "jn_sid")).toBeUndefined();
  });

  test("a choice returns the reader to the page they were on", async ({ page }) => {
    await page.goto("/en/search?q=climate");
    await page.getByRole("button", { name: "Decline" }).click();
    await expect(page.getByRole("region", { name: "Cookie choice" })).toBeHidden();
    await expect(page).toHaveURL(/\/en\/search\?q=climate$/);
  });

  test("another site cannot post a choice on the reader's behalf", async ({ request }) => {
    const response = await request.post("/api/consent", {
      form: { choice: "granted" },
      headers: { Origin: "https://elsewhere.example" },
      maxRedirects: 0,
    });
    expect(response.status()).toBe(403);
  });
});
