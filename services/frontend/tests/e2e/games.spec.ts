import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("games index lists recent finals and opens empty play-by-play", async ({ page }) => {
  await mockApi(page);
  await page.goto("/games");
  await expect(page.getByRole("heading", { name: "Game flow" })).toBeVisible();
  await expect(page.getByText("Recent final games")).toBeVisible();
  await expect(page.getByText("Not live win probability.")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Margin" })).toBeVisible();
  // Scoped to the recent-games table: the blown-leads table below also names teams.
  const recent = page.getByRole("table").first();
  await expect(recent.getByText("LAL", { exact: true })).toBeVisible();
  await expect(recent.getByText("GSW", { exact: true })).toBeVisible();
  await expectNo2010Range(page);

  await expect(page.getByRole("heading", { name: "Biggest blown leads" })).toBeVisible();
  const collapses = page.getByRole("table").nth(1);
  await expect(collapses.getByRole("cell", { name: "MIA", exact: true })).toBeVisible();
  await expect(collapses.getByRole("cell", { name: "21", exact: true })).toBeVisible();

  await recent.getByRole("link", { name: "Play-by-play →" }).first().click();
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

test("game flow page narrates the comeback and charts the differential", async ({ page }) => {
  await mockApi(page);
  await page.goto("/games/0022400002");

  await expect(page.getByRole("heading", { name: /Miami Heat|MIA/ })).toBeVisible();
  // The badge is the comeback story: deficit erased plus where it stood entering Q4.
  await expect(page.getByText("BOS erased a 21-point deficit, down 9 entering Q4")).toBeVisible();
  await expect(page.getByText("Max lead +21")).toBeVisible();
  await expect(page.getByText("4 lead changes")).toBeVisible();
  await expect(page.getByText("97 plays")).toBeVisible();
  await expect(page.getByText("No play-by-play data available.")).toHaveCount(0);
});

test("blown-leads table links through to that game", async ({ page }) => {
  await mockApi(page);
  await page.goto("/games");

  const collapses = page.getByRole("table").nth(1);
  await expect(collapses.getByRole("cell", { name: "Q3", exact: true })).toBeVisible();
  await collapses.getByRole("link", { name: "Play-by-play →" }).first().click();
  await expect(page).toHaveURL(/\/games\/0022400002/);
  await expect(page.getByText("BOS erased a 21-point deficit, down 9 entering Q4")).toBeVisible();
});
