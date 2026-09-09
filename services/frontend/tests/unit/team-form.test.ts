import { describe, expect, it } from "vitest";

import { lastTenFromGames, standingsSeed, streakFromGames } from "@/lib/team-form";

describe("team form from Regular Season finals", () => {
  it("computes last 10 and streak from newest-first results", () => {
    const games = [
      { is_win: true },
      { result: "W" },
      { is_win: false },
      { result: "L" },
      { is_win: true },
      { is_win: true },
      { is_win: false },
      { is_win: true },
      { is_win: true },
      { is_win: false },
      { is_win: false },
    ];
    expect(lastTenFromGames(games)).toBe("6–4");
    expect(streakFromGames(games)).toBe("W2");
    expect(lastTenFromGames([])).toBeNull();
    expect(streakFromGames([])).toBeNull();
    expect(streakFromGames([{ result: "L" }, { result: "L" }, { is_win: true }])).toBe("L2");
    expect(lastTenFromGames([{ result: "P" }])).toBeNull();
  });
});

describe("standingsSeed", () => {
  it("prefers the settled play-in seed over record rank", () => {
    // POR finished 8th on record but won the 7/8 game.
    expect(standingsSeed({ playoff_seed: 7, conference_rank: 8 })).toBe(7);
    expect(standingsSeed({ playoff_seed: 10, conference_rank: 9 })).toBe(10);
  });

  it("falls back to record rank before the play-in is decided", () => {
    expect(standingsSeed({ playoff_seed: null, conference_rank: 8 })).toBe(8);
    expect(standingsSeed({ conference_rank: 3 })).toBe(3);
    expect(standingsSeed({ playoff_seed: null, conference_rank: null })).toBeNull();
  });
});
