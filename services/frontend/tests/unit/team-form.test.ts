import { describe, expect, it } from "vitest";

import { lastTenFromGames, streakFromGames } from "@/lib/team-form";

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
