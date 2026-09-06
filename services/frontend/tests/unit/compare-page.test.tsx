import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getPlayer = vi.fn();
const comparePlayers = vi.fn();
const comparePlayersHeadToHead = vi.fn();

let search = new URLSearchParams("ids=201939");

vi.mock("next/navigation", () => ({
  usePathname: () => "/players/compare",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => search,
}));

vi.mock("@/lib/api", () => ({
  api: {
    comparePlayers: (...args: unknown[]) => comparePlayers(...args),
    comparePlayersHeadToHead: (...args: unknown[]) => comparePlayersHeadToHead(...args),
    searchPlayers: async () => ({ data: [], meta: { total: 0, limit: 8, offset: 0 } }),
    getPlayer: (...args: unknown[]) => getPlayer(...args),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import ComparePlayersPage from "@/app/players/compare/page";
import { Providers } from "@/components/providers";

const PLAYERS: Record<
  number,
  { player_id: number; full_name: string; position: string; team_abbreviation: string }
> = {
  201939: {
    player_id: 201939,
    full_name: "Stephen Curry",
    position: "G",
    team_abbreviation: "GSW",
  },
  202331: {
    player_id: 202331,
    full_name: "Kevin Durant",
    position: "F",
    team_abbreviation: "PHX",
  },
  202695: {
    player_id: 202695,
    full_name: "Kawhi Leonard",
    position: "F",
    team_abbreviation: "LAC",
  },
};

function careerRow(id: number, extras: Record<string, number | null>) {
  const player = PLAYERS[id];
  return {
    ...player,
    career_games_played: extras.games,
    seasons_played: extras.seasons,
    career_ppg: extras.ppg,
    career_rpg: extras.rpg,
    career_apg: extras.apg,
    career_avg_plus_minus: extras.plus_minus,
  };
}

function renderPage() {
  return render(
    <Providers>
      <ComparePlayersPage />
    </Providers>
  );
}

describe("compare page", () => {
  beforeEach(() => {
    search = new URLSearchParams("ids=201939");
    getPlayer.mockReset();
    comparePlayers.mockReset();
    comparePlayersHeadToHead.mockReset();
    getPlayer.mockImplementation(async (id: number) => ({
      ...PLAYERS[id],
      is_active: true,
      first_name: PLAYERS[id]?.full_name.split(" ")[0],
      last_name: PLAYERS[id]?.full_name.split(" ")[1],
      career_games_played: 100,
      seasons_played: 1,
      career_ppg: 25,
      career_rpg: 5,
      career_apg: 5,
    }));
    comparePlayers.mockResolvedValue({ data: [], meta: { total: 0, limit: 0, offset: 0 } });
    comparePlayersHeadToHead.mockResolvedValue({
      games_played: 0,
      players: [],
      games: [],
    });
  });

  it("shows full_name for a single selected id instead of #id", async () => {
    renderPage();

    await waitFor(() => {
      expect(getPlayer).toHaveBeenCalledWith(201939);
    });
    expect(await screen.findByText("Stephen Curry")).toBeInTheDocument();
    expect(screen.queryByText("#201939")).not.toBeInTheDocument();
    expect(comparePlayers).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Head-to-head" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Compare mode" })).not.toBeInTheDocument();
  });

  it("hides the head-to-head toggle when three players are selected", async () => {
    search = new URLSearchParams("ids=201939,202331,202695");
    comparePlayers.mockResolvedValue({
      data: [
        careerRow(202331, {
          games: 79,
          seasons: 1,
          ppg: 25.9,
          rpg: 5.5,
          apg: 4.8,
          plus_minus: 4.1,
        }),
        careerRow(201939, {
          games: 45,
          seasons: 1,
          ppg: 26.5,
          rpg: 3.5,
          apg: 4.7,
          plus_minus: 3.2,
        }),
        careerRow(202695, {
          games: 40,
          seasons: 1,
          ppg: 24.1,
          rpg: 6.2,
          apg: 3.8,
          plus_minus: 1.8,
        }),
      ],
      meta: { total: 3, limit: 3, offset: 0 },
    });

    renderPage();

    expect(await screen.findByRole("link", { name: "Kevin Durant" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Stephen Curry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Head-to-head" })).not.toBeInTheDocument();
    expect(comparePlayersHeadToHead).not.toHaveBeenCalled();
    expect(comparePlayers).toHaveBeenCalled();
  });

  it("shows the toggle for two players and keeps career aggregates by default", async () => {
    search = new URLSearchParams("ids=201939,202331");
    comparePlayers.mockResolvedValue({
      data: [
        careerRow(202331, {
          games: 79,
          seasons: 1,
          ppg: 25.9,
          rpg: 5.5,
          apg: 4.8,
          plus_minus: 4.1,
        }),
        careerRow(201939, {
          games: 45,
          seasons: 1,
          ppg: 26.5,
          rpg: 3.5,
          apg: 4.7,
          plus_minus: 3.2,
        }),
      ],
      meta: { total: 2, limit: 2, offset: 0 },
    });

    renderPage();

    expect(await screen.findByRole("button", { name: "Head-to-head" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Career" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Kevin Durant" })).toBeInTheDocument();
    expect(screen.getByText("79")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "+/-" })).toBeInTheDocument();
    expect(screen.getByText("+4.1")).toBeInTheDocument();
    expect(screen.getByText("+3.2")).toBeInTheDocument();
    expect(screen.getByText("+0.9")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "+/-" })).toBeInTheDocument();
    expect(screen.getByText(/Totals cover the seasons we have game logs for/)).toBeInTheDocument();
    expect(comparePlayersHeadToHead).not.toHaveBeenCalled();
  });

  it("renders career +/- as an em dash when the average is missing", async () => {
    search = new URLSearchParams("ids=201939,202331");
    comparePlayers.mockResolvedValue({
      data: [
        careerRow(202331, {
          games: 79,
          seasons: 1,
          ppg: 25.9,
          rpg: 5.5,
          apg: 4.8,
          plus_minus: 4.1,
        }),
        careerRow(201939, {
          games: 45,
          seasons: 1,
          ppg: 26.5,
          rpg: 3.5,
          apg: 4.7,
          plus_minus: null,
        }),
      ],
      meta: { total: 2, limit: 2, offset: 0 },
    });

    renderPage();

    expect(await screen.findByRole("link", { name: "Kevin Durant" })).toBeInTheDocument();
    expect(screen.getByText("+4.1")).toBeInTheDocument();
    const differenceCells = screen.getByText("Difference").closest("tr")?.querySelectorAll("td");
    const plusMinusDiff = differenceCells?.[differenceCells.length - 1];
    expect(plusMinusDiff?.textContent).toBe("—");
    expect(plusMinusDiff?.textContent).not.toBe("+0.0");
    expect(plusMinusDiff?.textContent).not.toBe("+0");
  });

  it("renders head-to-head averages and game logs after toggling", async () => {
    search = new URLSearchParams("ids=201939,202331");
    comparePlayers.mockResolvedValue({
      data: [
        careerRow(202331, {
          games: 79,
          seasons: 1,
          ppg: 25.9,
          rpg: 5.5,
          apg: 4.8,
          plus_minus: 4.1,
        }),
        careerRow(201939, {
          games: 45,
          seasons: 1,
          ppg: 26.5,
          rpg: 3.5,
          apg: 4.7,
          plus_minus: 3.2,
        }),
      ],
      meta: { total: 2, limit: 2, offset: 0 },
    });
    comparePlayersHeadToHead.mockResolvedValue({
      games_played: 1,
      players: [
        {
          player_id: 201939,
          full_name: "Stephen Curry",
          games: 1,
          mpg: 36.0,
          ppg: 32.0,
          rpg: 4.0,
          apg: 8.0,
          plus_minus: 10.0,
        },
        {
          player_id: 202331,
          full_name: "Kevin Durant",
          games: 1,
          mpg: 38.0,
          ppg: 30.0,
          rpg: 9.0,
          apg: 6.0,
          plus_minus: -8.0,
        },
      ],
      games: [
        {
          game_id: "0022400001",
          game_date: "2024-10-22",
          season: "2024-25",
          matchup: "GSW vs. PHX",
          lines: [
            {
              player_id: 201939,
              full_name: "Stephen Curry",
              team_abbreviation: "GSW",
              opponent_abbreviation: "PHX",
              location: "home",
              result: "W",
              minutes: 36,
              points: 32,
              rebounds: 4,
              assists: 8,
              plus_minus: 10,
            },
            {
              player_id: 202331,
              full_name: "Kevin Durant",
              team_abbreviation: "PHX",
              opponent_abbreviation: "GSW",
              location: "away",
              result: "L",
              minutes: 38,
              points: 30,
              rebounds: 9,
              assists: 6,
              plus_minus: -8,
            },
          ],
        },
      ],
    });

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Head-to-head" }));

    await waitFor(() => {
      expect(comparePlayersHeadToHead).toHaveBeenCalledWith([201939, 202331]);
    });
    expect(await screen.findByText("GSW vs. PHX")).toBeInTheDocument();
    expect(screen.getByText("2024-25")).toBeInTheDocument();
    expect(screen.getByText("32.0")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader", { name: "+/-" })).toHaveLength(2);
    expect(screen.getByText("+10.0")).toBeInTheDocument();
    expect(screen.getByText("-8.0")).toBeInTheDocument();
    expect(screen.getByText("+10")).toBeInTheDocument();
    expect(screen.getByText("-8")).toBeInTheDocument();
    expect(screen.getByText(/opposite teams/)).toBeInTheDocument();
    expect(screen.queryByText(/Totals cover seasons loaded/)).not.toBeInTheDocument();
  });

  it("shows an empty state when two players have no head-to-head meetings", async () => {
    search = new URLSearchParams("ids=201939,202331&view=h2h");
    comparePlayersHeadToHead.mockResolvedValue({
      games_played: 0,
      players: [
        {
          player_id: 201939,
          full_name: "Stephen Curry",
          games: 0,
          mpg: null,
          ppg: null,
          rpg: null,
          apg: null,
          plus_minus: null,
        },
        {
          player_id: 202331,
          full_name: "Kevin Durant",
          games: 0,
          mpg: null,
          ppg: null,
          rpg: null,
          apg: null,
          plus_minus: null,
        },
      ],
      games: [],
    });

    renderPage();

    expect(
      await screen.findByText("No head-to-head games to show. Teammate games are not counted.")
    ).toBeInTheDocument();
    expect(comparePlayers).not.toHaveBeenCalled();
  });
});
