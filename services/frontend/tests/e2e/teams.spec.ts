import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("teams directory to profile shows cap position", async ({ page }) => {
  await mockApi(page);
  await page.goto("/teams");
  await expect(page).toHaveTitle("Baseline — Teams");
  await expect(page.getByRole("heading", { name: "Teams" })).toBeVisible();
  await expect(page.getByText(/Records shown for/)).toHaveCount(0);
  await expect(page.getByText(/30 clubs/)).toHaveCount(0);
  await expect(page.getByRole("link", { name: "GSW" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Team offensive vs defensive rating" })
  ).toBeVisible();
  await expectNo2010Range(page);

  await page.getByRole("link", { name: "GSW" }).click();
  await expect(page.getByRole("heading", { name: "Golden State Warriors" })).toBeVisible();
  await expect(page.getByText(/Chase Center/)).toBeVisible();
  await expect(page.getByText("Cap position").first()).toBeVisible();
  await expect(page.getByText("Regular Season")).toBeVisible();
  await expect(page.getByText("Arena city")).toBeVisible();
});

test("standings page lists conferences without a 2010-11 range", async ({ page }) => {
  await mockApi(page);
  await page.goto("/standings");
  await expect(page.getByRole("heading", { name: "Standings" })).toBeVisible();
  await expect(page.getByText("Eastern Conference")).toBeVisible();
  await expect(page.getByText("Western Conference")).toBeVisible();
  await expect(page.getByRole("link", { name: "CHI" })).toBeVisible();
  await expect(page.getByRole("link", { name: "GSW" })).toBeVisible();
  await expectNo2010Range(page);
});

test("teams directory empty warehouse", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/teams");
  await expect(page.getByText("No teams to show yet.")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Team offensive vs defensive rating" })
  ).toHaveCount(0);
});

test("teams page plots each team as a bare logo marker", async ({ page }) => {
  await mockApi(page);
  await page.goto("/teams");

  const scatter = page.locator("section[aria-labelledby='team-ratings-heading']");
  await expect(scatter).toBeVisible();
  await expect(scatter.getByText("Offensive rating")).toBeVisible();
  // Markers are the logo image alone; the backing circle was removed.
  await expect(scatter.locator("image")).toHaveCount(2);
  await expect(scatter.locator("circle")).toHaveCount(0);
});
