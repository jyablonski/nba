import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getStatus = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    getStatus: () => getStatus(),
  },
}));

import AboutPage from "@/app/about/page";
import { Providers } from "@/components/providers";

describe("about page", () => {
  it("shows Baseline copy and the header watermark string", async () => {
    getStatus.mockResolvedValue({
      last_scraped_at: "2026-09-06T02:10:00Z",
      player_count: 1,
      game_count: 1,
      season_count: 1,
      first_season: "2010-11",
      last_season: "2025-26",
    });

    render(
      <Providers>
        <AboutPage />
      </Providers>
    );

    await waitFor(() => {
      expect(screen.getByText("Scraped 6 Sep 2026, 02:10 UTC")).toBeInTheDocument();
    });
    const about = screen.getByRole("article");
    expect(about.textContent).not.toMatch(/—|&mdash;/);
    expect(screen.getByRole("heading", { name: "Baseline" })).toBeInTheDocument();
    expect(screen.queryByText("Working title, not final")).not.toBeInTheDocument();
    expect(screen.queryByText("Courtline")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sources" })).toBeInTheDocument();
    const sources = screen.getByRole("heading", { name: "Sources" }).closest("section");
    expect(sources).toBeTruthy();
    expect(within(sources!).getByText("Basketball-Reference")).toBeInTheDocument();
    expect(within(sources!).getByText("The Odds API")).toBeInTheDocument();
    expect(within(sources!).getByText(/r\/nba posts/)).toBeInTheDocument();
    expect(within(sources!).getByText(/No Baseline Social page yet/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "How the data gets here" })).toBeInTheDocument();
    expect(screen.getByText(/collected and served here/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Coverage" })).toBeInTheDocument();
    expect(screen.getByText(/Coverage defaults to the latest season/)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "About the salary figures" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/2010-11/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Postgres/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/dbt/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/FastAPI/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Cube/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Alembic/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Last scraped" })).toBeInTheDocument();
    expect(screen.queryByText("Name options")).not.toBeInTheDocument();
    expect(screen.queryByText("The Scorebook")).not.toBeInTheDocument();
    expect(screen.queryByText("Sideline")).not.toBeInTheDocument();
    expect(screen.queryByText("Hardwood Index")).not.toBeInTheDocument();
    expect(screen.queryByText("Box Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("Current")).not.toBeInTheDocument();
    expect(screen.queryByText("Planned (not built)")).not.toBeInTheDocument();
    expect(screen.queryByText("Player search, splits, compare")).not.toBeInTheDocument();
  });

  it("shows Scraped — when the warehouse watermark is missing", async () => {
    getStatus.mockResolvedValue({
      last_scraped_at: null,
      player_count: 0,
      game_count: 0,
      season_count: 0,
      first_season: null,
      last_season: null,
    });

    render(
      <Providers>
        <AboutPage />
      </Providers>
    );

    await waitFor(() => {
      expect(getStatus).toHaveBeenCalled();
    });
    expect(screen.getByText("Scraped —")).toBeInTheDocument();
  });
});
