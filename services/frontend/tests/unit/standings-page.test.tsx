import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/standings",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("season=2025-26"),
}));

vi.mock("@/lib/api", () => ({
  api: {
    listSeasons: async () => ({
      data: [{ season: "2025-26" }],
      meta: { total: 1, limit: 1, offset: 0 },
    }),
    listStandings: async () => ({
      data: [
        {
          team_id: 1610612738,
          abbreviation: "BOS",
          team_name: "Boston Celtics",
          season: "2025-26",
          season_type: "Regular Season",
          as_of_date: null,
          conference: "East",
          division: "Atlantic",
          conference_rank: 1,
          division_rank: null,
          wins: 56,
          losses: 26,
          win_pct: 0.683,
          games_back: 0,
          conf_games_back: null,
          streak: "W2",
          last_10: "8-2",
          record_source: "games",
        },
      ],
      meta: { total: 1, limit: 50, offset: 0 },
    }),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import StandingsPage from "@/app/standings/page";
import { Providers } from "@/components/providers";

describe("standings page", () => {
  it("shows Regular Season W–L when official ranks are missing", async () => {
    render(
      <Providers>
        <StandingsPage />
      </Providers>
    );
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "BOS" })).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "BOS" })).toHaveTextContent("BOS");
    expect(screen.getByRole("link", { name: "BOS" }).querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg"
    );
    expect(screen.queryByLabelText("Season")).not.toBeInTheDocument();
    expect(screen.getByText("56–26")).toBeInTheDocument();
    expect(screen.getByText("W2")).toBeInTheDocument();
    expect(screen.getByText("8-2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "BOS" }).closest("tr")).toHaveTextContent("1");
    expect(screen.queryByText(/Official ranks aren't available yet/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Conference rank and Regular Season W–L are from game results/)
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Official ranks were not ingested/)).not.toBeInTheDocument();
    expect(screen.queryByText("No standings yet")).not.toBeInTheDocument();
  });
});
