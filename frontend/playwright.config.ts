import { defineConfig } from "@playwright/test";

// reuseExistingServer is unconditional, not gated on !CI: ci.yml's web job
// already builds and starts the app on this same port for scripts/smoke-web.sh,
// and this suite runs right after it in the same job - reusing that instance
// means the app gets built once per CI run, not twice. Running this file cold
// (no server up yet) still works: Playwright falls back to the command below.
export default defineConfig({
  testDir: "./e2e",
  // Runs under its own config (playwright.structured-data.config.ts) against
  // a second server with a live stub API behind it - every test here runs
  // with none, deliberately (see accessibility.spec.ts).
  testIgnore: "structured-data.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "pnpm build && pnpm start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
