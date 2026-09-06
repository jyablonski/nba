import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const searchPlayers = vi.fn();
const listTeams = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/players",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    listSeasons: async () => ({
      data: [{ season: "2025-26" }],
      meta: { total: 1, limit: 1, offset: 0 },
    }),
    searchPlayers: (...args: unknown[]) => searchPlayers(...args),
    listTeams: (...args: unknown[]) => listTeams(...args),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import PlayersPage from "@/app/players/page";
import { Providers } from "@/components/providers";

describe("players directory", () => {
  it("defaults Active only on, sorts teams A–Z, and keeps APG and Status apart", async () => {
    searchPlayers.mockResolvedValue({
      data: [
        {
          player_id: 2544,
          full_name: "LeBron James",
          position: "F",
          team_abbreviation: "LAL",
          is_active: true,
          career_games_played: 70,
          career_ppg: 21.3,
          career_rpg: 6.2,
          career_apg: 7.2,
        },
      ],
      meta: { total: 1, limit: 25, offset: 0 },
    });
    listTeams.mockResolvedValue({
      data: [
        {
          team_id: 1610612764,
          abbreviation: "WAS",
          team_name: "Washington Wizards",
          conference: "East",
          division: "Southeast",
        },
        {
          team_id: 1610612738,
          abbreviation: "BOS",
          team_name: "Boston Celtics",
          conference: "East",
          division: "Atlantic",
        },
        {
          team_id: 1610612737,
          abbreviation: "ATL",
          team_name: "Atlanta Hawks",
          conference: "East",
          division: "Southeast",
        },
      ],
      meta: { total: 3, limit: 3, offset: 0 },
    });

    render(
      <Providers>
        <PlayersPage />
      </Providers>
    );

    expect(screen.getByRole("checkbox", { name: "Active only" })).toBeChecked();
    await waitFor(() => {
      expect(searchPlayers).toHaveBeenCalledWith("", {
        active: true,
        team_id: undefined,
        limit: 25,
        offset: 0,
      });
    });
    expect(await screen.findByRole("columnheader", { name: "APG" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeInTheDocument();
    expect(screen.getByText("7.2")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.queryByText("7.2Active")).not.toBeInTheDocument();
    expect(screen.queryByText("APGSTATUS")).not.toBeInTheDocument();

    const teamSelect = await screen.findByRole("combobox");
    await waitFor(() => {
      expect(
        within(teamSelect)
          .getAllByRole("option")
          .map((option) => option.textContent)
      ).toEqual(["Team All", "ATL", "BOS", "WAS"]);
    });
  });
});
