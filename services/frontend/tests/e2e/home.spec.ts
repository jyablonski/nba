import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("home desk uses latest-season coverage, not a 2010-11 range", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByText("Latest games")).toBeVisible();
  await expect(page.getByText("Standings snapshot")).toBeVisible();
  await expect(page.getByText("Latest completed games this season.")).toBeVisible();
  await expect(page.locator("dt:text-is('Coverage:') + dd")).toHaveText("2025-26");
  await expectNo2010Range(page);
  await expect(page.getByRole("link", { name: "PBP" })).toBeVisible();
  await expect(page.getByText("LAL")).toBeVisible();
  await expect(page.getByText("at", { exact: true })).toBeVisible();
  await expect(page.getByText("GSW").first()).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Type" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Regular Season" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Full standings →" })).toBeVisible();
});

test("home empty warehouse shows latest-season empty copy", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/");
  await expect(page.getByText("No games yet for this season.")).toBeVisible();
  await expect(page.getByText("No standings yet")).toBeVisible();
  await expect(page.locator("dt:text-is('Coverage:') + dd")).not.toHaveText(/2010-11/);
  await expectNo2010Range(page);
});

test("home standings snapshot deep-links to /standings", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Full standings →" }).click();
  await expect(page).toHaveURL(/\/standings/);
  await expect(page.getByRole("heading", { name: "Standings" })).toBeVisible();
  await expect(page.getByText("Eastern Conference")).toBeVisible();
  await expect(page.getByText("Western Conference")).toBeVisible();
  await expectNo2010Range(page);
});
