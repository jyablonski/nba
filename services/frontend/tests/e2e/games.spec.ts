import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("games index lists recent finals and opens empty play-by-play", async ({ page }) => {
  await mockApi(page);
  await page.goto("/games");
  await expect(page.getByRole("heading", { name: "Game flow" })).toBeVisible();
  await expect(page.getByText("Recent final games")).toBeVisible();
  await expect(page.getByText("Not live win probability.")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Margin" })).toBeVisible();
  await expect(page.getByText("LAL")).toBeVisible();
  await expect(page.getByText("GSW")).toBeVisible();
  await expectNo2010Range(page);

  await page.getByRole("link", { name: "Play-by-play →" }).click();
  await expect(page).toHaveURL(/\/games\/0022400001/);
  await expect(page.getByText("No play-by-play data available.")).toBeVisible();
  await expect(page.getByText("There's no scoring timeline for this game.")).toBeVisible();
  await expect(page.getByRole("link", { name: "All recent final games →" })).toBeVisible();
  await expect(page.getByText("Recent final games", { exact: true })).toHaveCount(0);
});

test("games index empty warehouse", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/games");
  await expect(page.getByText("No completed games to show yet.")).toBeVisible();
});
