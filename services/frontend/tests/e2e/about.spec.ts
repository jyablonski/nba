import { expect, test } from "@playwright/test";

import { expectNo2010Range, mockApi } from "./helpers";

test("About lists ingest sources without salary jargon or 2010-11 copy", async ({ page }) => {
  await mockApi(page);
  await page.goto("/about");
  const about = page.getByRole("article");
  await expect(page.getByRole("heading", { name: "Baseline" })).toBeVisible();
  await expect(page.getByText("Working title, not final")).toHaveCount(0);
  await expect(page.getByText("Courtline")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  await expect(about.getByText("NBA Stats")).toBeVisible();
  await expect(about.getByText("Basketball-Reference")).toBeVisible();
  await expect(about.getByText("The Odds API")).toBeVisible();
  await expect(about.getByText(/r\/nba posts/)).toBeVisible();
  await expect(about.getByText(/collected and served here/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "How the data gets here" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Coverage" })).toBeVisible();
  await expect(page.getByText(/Coverage defaults to the latest season/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "About the salary figures" })).toHaveCount(0);
  await expect(about.getByText(/Postgres/i)).toHaveCount(0);
  await expect(about.getByText(/dbt/i)).toHaveCount(0);
  await expect(about.getByText(/FastAPI/i)).toHaveCount(0);
  await expectNo2010Range(page);
  await expect(about).not.toContainText("—");
});

test("About shows Scraped — when the warehouse watermark is missing", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/about");
  await expect(page.getByRole("article").getByText("Scraped —")).toBeVisible();
  await expectNo2010Range(page);
});
