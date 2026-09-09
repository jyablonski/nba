import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("players directory to profile shows remaining-contract snapshot and B2B", async ({ page }) => {
  await mockApi(page);
  await page.goto("/players");
  await expect(page.getByRole("heading", { name: "Players" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Kawhi Leonard" }).first()).toBeVisible();
  await expect(page.getByLabel("Active only")).toBeVisible();
  await expectNo2010Range(page);

  await page.getByRole("link", { name: "Kawhi Leonard" }).first().click();
  await expect(page.getByRole("heading", { name: "Kawhi Leonard" })).toBeVisible();
  await expect(page.getByText("Back-to-back splits", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Remaining contract" })).toBeVisible();
  await expect(page.getByText(/Basketball-Reference remaining-year snapshot/)).toBeVisible();
  await expect(page.getByText(/Unmatched names show/)).toHaveCount(0);
});

test("players directory can compare two selected names", async ({ page }) => {
  await mockApi(page);
  await page.goto("/players");
  await page.getByRole("row").filter({ hasText: "Kawhi Leonard" }).getByRole("checkbox").click();
  await page.getByRole("row").filter({ hasText: "Stephen Curry" }).getByRole("checkbox").click();
  await page.getByRole("button", { name: "Compare selected →" }).click();
  await expect(page).toHaveURL(/\/players\/compare/);
  await expect(page.getByRole("link", { name: "Kawhi Leonard" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Stephen Curry" })).toBeVisible();
});

test("players directory empty warehouse", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/players");
  await expect(page.getByText("No players yet")).toBeVisible();
});

test("player game log keeps the PBP link in the last column", async ({ page }) => {
  await mockApi(page);
  await page.goto("/players");
  await page.getByRole("link", { name: "Kawhi Leonard" }).first().click();
  await expect(page).toHaveURL(/\/players\//);

  const log = page
    .getByRole("table")
    .filter({ has: page.getByRole("columnheader", { name: "PBP" }) });
  const headers = log.getByRole("columnheader");
  await expect(headers.last()).toHaveText("PBP");
  await expect(headers.first()).toContainText("Date");
});
