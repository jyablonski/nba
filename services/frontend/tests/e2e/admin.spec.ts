import { expect, test } from "@playwright/test";

import { primaryNav } from "./helpers";

/**
 * The /admin gate, end to end.
 *
 * These run against the real middleware and the real NextAuth config with no
 * ADMIN_GITHUB_LOGINS set, which is the fail-closed case: the allowlist is
 * empty, so every visitor is rejected. Unlike the other specs there is no API
 * mocking, because the redirect happens in middleware before any data fetch —
 * and the admin page is a server component, so mocking window.fetch could not
 * reach it anyway.
 */

test("unauthenticated /admin redirects to the sign-in page", async ({ page }) => {
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin\/signin/);
  await expect(page.getByRole("heading", { name: "Admin sign in" })).toBeVisible();
  // The operational data must never render for an anonymous visitor.
  await expect(page.getByRole("heading", { name: "System status" })).toHaveCount(0);
  await expect(page.getByText("Ingestion gate")).toHaveCount(0);
});

test("the sign-in page itself is reachable without a session", async ({ page }) => {
  // If this were gated too, every visitor would hit a redirect loop.
  await page.goto("/admin/signin");
  await expect(page).toHaveURL(/\/admin\/signin/);
  await expect(page.getByRole("button", { name: /Continue with GitHub/i })).toBeVisible();
});

test("nested admin routes are gated, including signin-prefixed paths", async ({ page }) => {
  // Regression: a loose (?!signin) matcher left /admin/signin-anything open.
  for (const path of ["/admin/jobs", "/admin/signin-backdoor", "/admin/a/b"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/admin\/signin/);
  }
});

test("admin is not advertised in the public navigation", async ({ page }) => {
  await page.goto("/");
  await expect(primaryNav(page).getByRole("link", { name: /admin/i })).toHaveCount(0);
});

test("an access-denied sign-in shows the allowlist message", async ({ page }) => {
  // NextAuth redirects here with ?error=AccessDenied when signIn() rejects an
  // account that is not on the allowlist.
  await page.goto("/admin/signin?error=AccessDenied");
  await expect(page.getByText(/not on the admin allowlist/i)).toBeVisible();
});
