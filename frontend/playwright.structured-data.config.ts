import { defineConfig } from "@playwright/test";

// A second, narrow config for exactly one spec file - the structured-data
// check needs a live API, and every other e2e test in this app deliberately
// runs with none (see accessibility.spec.ts). Reusing the default config's
// server for this would either give every other test real data it isn't
// written for, or give this one test the degraded state it exists to rule
// out. Two servers on two ports is the honest way to keep both true.
//
// `next start` here does not rebuild - it reuses the `.next` output the
// default config's webServer already built in the same CI job.
// process.env.API_URL is read per-request server-side, not inlined at build
// time, so pointing a second `next start` at the stub needs no rebuild.
export default defineConfig({
  testDir: "./e2e",
  testMatch: "structured-data.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3002",
  },
  webServer: [
    {
      command: "node ../scripts/stub-api.mjs",
      port: 8089,
      reuseExistingServer: false,
      env: { STUB_PORT: "8089" },
    },
    {
      command: "next start --port 3002",
      url: "http://127.0.0.1:3002/en",
      reuseExistingServer: false,
      timeout: 60_000,
      env: { API_URL: "http://127.0.0.1:8089" },
    },
  ],
});
