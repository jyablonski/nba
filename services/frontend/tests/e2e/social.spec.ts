import { expect, test } from "@playwright/test";

import { mockApi, primaryNav } from "./helpers";

test("social reaches from the nav and labels its sampling honestly", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await primaryNav(page).getByRole("link", { name: "Social" }).click();

  await expect(page).toHaveURL(/\/social/);
  await expect(page.getByRole("heading", { name: "Social", level: 1 })).toBeVisible();

  // The gap between captured and posted comments has to stay on screen.
  await expect(page.getByText(/top 10 per post, of 18,204 posted/i)).toBeVisible();
  // Comments stay collapsed until asked for.
  await expect(page.getByText(/the rest of the thread is not stored/i)).toHaveCount(0);
  await page.getByRole("button", { name: /show top 1 of 132/i }).click();
  await expect(page.getByText(/top 1 of 132 comments/i)).toBeVisible();
  await expect(page.getByText(/the rest of the thread is not stored/i)).toBeVisible();

  // A zero-score post keeps its discussion ratio and blanks the score ratios.
  await expect(page.getByText("132.00")).toBeVisible();
  await expect(page.getByText(/undefined, so they are left blank/i)).toBeVisible();

  await expect(page.getByRole("heading", { name: "Player mentions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fanbases" })).toBeVisible();
  await expect(page.getByText(/what this page cannot tell you/i)).toBeVisible();
});

test("social filters write to the URL", async ({ page }) => {
  await mockApi(page);
  await page.goto("/social");
  await page.getByRole("button", { name: /highlight 12/i }).click();
  await expect(page).toHaveURL(/type=highlight/);
  await page.getByRole("button", { name: "24h", exact: true }).click();
  await expect(page).toHaveURL(/range=24h/);
});

test("social explains a quiet range instead of rendering an empty shell", async ({ page }) => {
  await mockApi(page, { empty: true });
  await page.goto("/social");
  await expect(page.getByText(/nothing collected in this range/i)).toBeVisible();
  await expect(page.getByText(/nothing has been collected for these days yet/i)).toBeVisible();
});

test("the active filter chip is legible, not paper-on-paper", async ({ page }) => {
  await mockApi(page);
  await page.goto("/social");

  // A typo'd design token (bg-ink, which this theme does not define) leaves the
  // chip background transparent while the label keeps its paper colour, so the
  // active chip renders blank. Type checking and unit tests cannot see that.
  for (const chip of [
    page.getByRole("button", { name: "7d" }),
    page.getByRole("button", { name: /^All/ }),
  ]) {
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    const style = await chip.evaluate((node) => {
      const computed = getComputedStyle(node);
      return { color: computed.color, background: computed.backgroundColor };
    });
    expect(style.color).not.toBe(style.background);
    expect(style.background).not.toBe("rgba(0, 0, 0, 0)");
  }

  await expect(page.getByRole("button", { name: "7d" })).toContainText("7d");
  await expect(page.getByRole("button", { name: /^All/ })).toContainText("All");
});
