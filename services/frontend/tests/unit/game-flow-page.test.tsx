import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/games/0042500405",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "0042500405" }),
}));

const getGameFlow = vi.fn();
const getGamePlayByPlay = vi.fn();
const listGames = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    listGames: (...args: unknown[]) => listGames(...args),
    getGameFlow: (...args: unknown[]) => getGameFlow(...args),
    getGamePlayByPlay: (...args: unknown[]) => getGamePlayByPlay(...args),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import GameFlowPage from "@/app/games/[id]/page";
import { GameFlowTooltip } from "@/components/charts/game-flow-chart";
import { FALLBACK_AWAY, FALLBACK_HOME } from "@/lib/team-colors";
import { Providers } from "@/components/providers";

describe("game flow page", () => {
  it("shows empty play-by-play copy and no Recent final games filter", async () => {
    getGameFlow.mockResolvedValue({
      game_id: "0042500405",
      season: "2025-26",
      game_date: "2026-06-13",
      home_team_id: 1610612759,
      away_team_id: 1610612752,
      home_team_abbreviation: "SAS",
      away_team_abbreviation: "NYK",
      home_team_name: "San Antonio Spurs",
      away_team_name: "New York Knicks",
      has_play_by_play: false,
    });
    getGamePlayByPlay.mockResolvedValue({
      data: [],
      meta: { total: 0, limit: 0, offset: 0 },
    });

    render(
      <Providers>
        <GameFlowPage />
      </Providers>
    );

    await waitFor(() => {
      expect(screen.getByText("No play-by-play data available.")).toBeInTheDocument();
    });
    expect(screen.getByText("There's no scoring timeline for this game.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All recent final games →" })).toHaveAttribute(
      "href",
      "/games"
    );
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByText("Recent final games")).not.toBeInTheDocument();
    expect(screen.queryByText(/dbt/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/scrape/i)).not.toBeInTheDocument();
    expect(listGames).not.toHaveBeenCalled();
  });

  it("computes the biggest run from PBP and ignores a marathon gold label", async () => {
    getGameFlow.mockResolvedValue({
      game_id: "0042500405",
      season: "2025-26",
      game_date: "2026-06-13",
      home_team_id: 1610612759,
      away_team_id: 1610612752,
      home_team_abbreviation: "SAS",
      away_team_abbreviation: "NYK",
      home_team_name: "San Antonio Spurs",
      away_team_name: "New York Knicks",
      has_play_by_play: true,
      biggest_run_label: "NYK 79-59",
      biggest_run_start_seconds: 900,
      biggest_run_end_seconds: 2800,
    });
    getGamePlayByPlay.mockResolvedValue({
      data: [
        {
          game_id: "0042500405",
          action_number: 1,
          period: 1,
          clock: "PT11M50.00S",
          elapsed_seconds: 10,
          score_home: 0,
          score_away: 3,
          score_differential: -3,
          description: "J. Brunson 3PT Jump Shot (3 PTS)",
        },
        {
          game_id: "0042500405",
          action_number: 2,
          period: 1,
          clock: "PT11M40.00S",
          elapsed_seconds: 20,
          score_home: 1,
          score_away: 3,
          score_differential: -2,
        },
        {
          game_id: "0042500405",
          action_number: 3,
          period: 1,
          clock: "PT11M30.00S",
          elapsed_seconds: 30,
          score_home: 1,
          score_away: 6,
          score_differential: -5,
        },
        {
          game_id: "0042500405",
          action_number: 4,
          period: 1,
          clock: "PT11M20.00S",
          elapsed_seconds: 40,
          score_home: 2,
          score_away: 6,
          score_differential: -4,
        },
        {
          game_id: "0042500405",
          action_number: 5,
          period: 1,
          clock: "PT08M36.00S",
          elapsed_seconds: 60,
          score_home: 2,
          score_away: 16,
          score_differential: -14,
          description: "J. Brunson 2pt Driving Layup",
        },
      ],
      meta: { total: 5, limit: 5, offset: 0 },
    });

    render(
      <Providers>
        <GameFlowPage />
      </Providers>
    );

    await waitFor(() => {
      expect(screen.getByText("Biggest run: NYK 16-2")).toBeInTheDocument();
    });
    expect(screen.queryByText(/79-59/)).not.toBeInTheDocument();
    expect(screen.queryByText(/PT08M36/)).not.toBeInTheDocument();
  });

  it("surfaces the PBP description on a scoring-play tooltip", () => {
    render(
      <GameFlowTooltip
        active
        payload={[
          {
            payload: {
              elapsed_seconds: 60,
              score_differential: -14,
              score_home: 2,
              score_away: 16,
              period: 1,
              clock: "PT08M36.00S",
              clock_remaining_seconds: 516,
              scoring_side: "away",
              player_name: null,
              action_type: "2pt",
              sub_type: "Driving Layup",
              description: "J. Brunson 2pt Driving Layup",
              away_abbreviation: "NYK",
              home_abbreviation: "SAS",
            },
          },
        ]}
      />
    );

    expect(screen.getByText("Q1 · 8:36")).toBeInTheDocument();
    const score = document.querySelector(".recharts-tooltip-item-value") as HTMLElement;
    expect(score).toHaveTextContent("NYK 16 – SAS 2 (-14)");
    // Abbreviations carry their side's plot colour, not the body ink.
    expect(within(score).getByText("NYK")).toHaveStyle({ color: FALLBACK_AWAY });
    expect(within(score).getByText("SAS")).toHaveStyle({ color: FALLBACK_HOME });
    expect(screen.getByText("J. Brunson 2pt Driving Layup")).toBeInTheDocument();
  });
});
