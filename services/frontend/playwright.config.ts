import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev -- --port 3100 --hostname localhost",
    url: "http://localhost:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      // Not a credential: NextAuth refuses to start without a secret, and
      // without one the /admin specs would pass because auth crashed rather
      // than because the allowlist rejected the visitor. ADMIN_GITHUB_LOGINS
      // is deliberately left unset — the empty allowlist IS the case under
      // test.
      AUTH_SECRET: "playwright-e2e-secret-not-used-by-any-deployment",
      AUTH_URL: "http://localhost:3100",
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
