import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClientError, api, queryErrorMessage } from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses envelopes and query strings", async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/players/compare/head-to-head")) {
        return jsonResponse({
          data: {
            games_played: 1,
            players: [{ player_id: 1, full_name: "A", games: 1, mpg: 36, ppg: 20, rpg: 5, apg: 4 }],
            games: [],
          },
        });
      }
      if (url.includes("/players/compare")) {
        return jsonResponse({ data: [{ player_id: 1, full_name: "A", career_games_played: 10 }] });
      }
      if (url.includes("/players/1/game-log")) {
        return jsonResponse([
          {
            game_date: "2024-10-22",
            opponent_abbreviation: "GSW",
            location: "home",
            result: "W",
            minutes: 30,
            points: 20,
            rebounds: 5,
            assists: 4,
            is_back_to_back: false,
          },
        ]);
      }
      if (url.includes("/players/1/back-to-backs")) {
        return jsonResponse({
          data: {
            player_id: 1,
            player_name: "A",
            season: null,
            total_back_to_backs: 2,
            games_played_in_b2b: 2,
            avg_pts_b2b: 20,
            avg_pts_non_b2b: 22,
          },
        });
      }
      if (url.endsWith("/players/1")) {
        return jsonResponse({
          data: {
            player_id: 1,
            full_name: "A",
            is_active: true,
            first_name: "A",
            last_name: "B",
            career_games_played: 1,
            seasons_played: 1,
            career_ppg: 1,
            career_rpg: 1,
            career_apg: 1,
          },
        });
      }
      if (url.includes("/players?")) {
        return jsonResponse({
          data: [
            {
              player_id: 1,
              full_name: "Kawhi Leonard",
              position: "F",
              team_abbreviation: "LAC",
              is_active: true,
            },
          ],
          meta: { total: 1, limit: 25, offset: 0 },
        });
      }
      if (url.includes("/teams/1/games")) {
        return jsonResponse({ data: [] });
      }
      if (url.includes("/teams/1/record")) {
        return jsonResponse({
          data: { team_id: 1, team_name: "GSW", wins: 1, losses: 0, win_pct: 1 },
        });
      }
      if (url.endsWith("/teams/1")) {
        return jsonResponse({
          team_id: 1,
          abbreviation: "GSW",
          team_name: "Warriors",
          conference: "West",
          division: "Pacific",
        });
      }
      if (url.includes("/teams")) {
        return jsonResponse({ data: [] });
      }
      if (url.includes("/standings")) {
        return jsonResponse({
          data: [
            {
              team_id: 1610612744,
              abbreviation: "GSW",
              team_name: "Golden State Warriors",
              season: "2024-25",
              conference: "West",
              conference_rank: 1,
              games_back: 0,
            },
          ],
        });
      }
      if (url.includes("/seasons")) {
        return jsonResponse({ data: ["2024-25"] });
      }
      if (url.includes("/play-by-play")) {
        return jsonResponse({
          data: [
            {
              game_id: "0022400001",
              action_number: 2,
              elapsed_seconds: 30,
              score_home: 2,
              score_away: 0,
              score_differential: 2,
            },
          ],
        });
      }
      if (url.includes("/flow")) {
        return jsonResponse({
          data: {
            game_id: "0022400001",
            season: "2024-25",
            game_date: "2024-10-22",
            home_team_id: 1,
            away_team_id: 2,
            has_play_by_play: true,
            biggest_run_label: "GSW 11-0",
          },
        });
      }
      if (url.includes("/schedule")) {
        return jsonResponse({
          data: [
            {
              game_id: "0022600100",
              season: "2026-27",
              game_date: "2026-10-22",
              status: "Scheduled",
              home_team_id: 1,
              away_team_id: 2,
            },
          ],
        });
      }
      if (url.includes("/games")) {
        return jsonResponse({ data: null });
      }
      if (url.includes("/season-stats")) {
        return jsonResponse({
          data: [{ player_id: 1, season: "2024-25", games_played: 3, ppg: 27.3 }],
        });
      }
      if (url.includes("/status")) {
        return jsonResponse({
          data: {
            last_scraped_at: "2026-09-04T04:12:00Z",
            player_count: 2,
            game_count: 3,
            season_count: 1,
            first_season: "2024-25",
            last_season: "2025-26",
          },
        });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.searchPlayers("kawhi", { active: true, team_id: 1610612744, limit: 10, offset: 0 })
    ).resolves.toMatchObject({
      meta: { total: 1 },
    });
    await expect(api.getPlayer(1)).resolves.toMatchObject({ full_name: "A" });
    await expect(
      api.getPlayerGameLog(1, {
        season: "2024-25",
        is_back_to_back: true,
        sort: "points",
        order: "desc",
        limit: 10,
        offset: 0,
      })
    ).resolves.toMatchObject({
      data: [{ points: 20 }],
    });
    await expect(api.getPlayerBackToBacks(1)).resolves.toMatchObject({ total_back_to_backs: 2 });
    await expect(api.comparePlayers([1, 2], "games_played")).resolves.toMatchObject({
      data: [{ player_id: 1 }],
    });
    await expect(api.comparePlayersHeadToHead([1, 2])).resolves.toMatchObject({
      games_played: 1,
      players: [{ player_id: 1 }],
    });
    expect(
      fetchMock.mock.calls.some((call) =>
        String(call[0]).includes("/players/compare/head-to-head?ids=1%2C2")
      )
    ).toBe(true);
    await expect(api.listTeams()).resolves.toMatchObject({ data: [] });
    await expect(api.listTeams({ season: "2025-26" })).resolves.toMatchObject({ data: [] });
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("/teams?season=2025-26"))
    ).toBe(true);
    await expect(api.getTeam(1)).resolves.toMatchObject({ abbreviation: "GSW" });
    await expect(
      api.getTeamGames(1, { location: "away", season_type: "Regular Season" })
    ).resolves.toMatchObject({ data: [] });
    await expect(api.getTeamGames(1, { arena_city: "Denver", limit: 200 })).resolves.toMatchObject({
      data: [],
    });
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("arena_city=Denver"))).toBe(
      true
    );
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("limit=200"))).toBe(true);
    await expect(api.getTeamRecord(1, { since_season: "2010-11" })).resolves.toMatchObject({
      wins: 1,
    });
    await expect(api.getTeamRecord(1, { arena_city: "Denver" })).resolves.toMatchObject({
      wins: 1,
    });
    await expect(
      api.listStandings({ season: "2024-25", conference: "West" })
    ).resolves.toMatchObject({ data: [{ abbreviation: "GSW" }] });
    await expect(api.listSeasons()).resolves.toMatchObject({ data: [{ season: "2024-25" }] });
    await expect(
      api.listGames({ season: "2024-25", season_type: "Regular Season", limit: 8 })
    ).resolves.toMatchObject({
      data: [],
    });
    await expect(
      api.listSchedule({ season: "2026-27", status: "Scheduled", limit: 50 })
    ).resolves.toMatchObject({
      data: [{ status: "Scheduled" }],
    });
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/api/v1/schedule"))).toBe(
      true
    );
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("season_type=Regular+Season"))
    ).toBe(true);
    await expect(api.getGamePlayByPlay("0022400001")).resolves.toMatchObject({
      data: [{ score_differential: 2 }],
    });
    await expect(api.getGameFlow("0022400001")).resolves.toMatchObject({
      biggest_run_label: "GSW 11-0",
    });
    await expect(api.getPlayerSeasonStats(1)).resolves.toMatchObject({
      data: [{ season: "2024-25" }],
    });
    await expect(api.getStatus()).resolves.toMatchObject({
      last_scraped_at: "2026-09-04T04:12:00Z",
      player_count: 2,
    });
  });

  it("handles 204, error bodies, and timeouts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 }))
    );
    await expect(api.listTeams()).resolves.toMatchObject({ data: [] });

    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response(JSON.stringify({ detail: "Player not found" }), { status: 404 })
      )
    );
    await expect(api.getPlayer(9)).rejects.toMatchObject({
      status: 404,
      message: "Player not found",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("nope", { status: 500 }))
    );
    await expect(api.getPlayer(9)).rejects.toMatchObject({ status: 500 });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new DOMException("timed out", "TimeoutError");
      })
    );
    await expect(api.listTeams()).rejects.toMatchObject({
      message: expect.stringContaining("timed out"),
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("offline");
      })
    );
    await expect(api.listTeams()).rejects.toMatchObject({
      message: expect.stringContaining("Unable to load data"),
    });
  });

  it("handles NLP error and success bodies", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ answer: "Not implemented", data: [], sql: null }, 501))
    );
    await expect(api.queryNlp("How many?")).rejects.toBeInstanceOf(ApiClientError);

    // Typed as fetch so mock.calls is a 2-tuple; the assertion below reads
    // calls[0][1], which does not exist on an untyped zero-arg mock.
    const nlpFetch = vi.fn<typeof fetch>(async () =>
      jsonResponse({ answer: "ok", data: [{ a: 1 }], sql: "select 1" })
    );
    vi.stubGlobal("fetch", nlpFetch);
    await expect(api.queryNlp("How many?", "2024-25")).resolves.toMatchObject({ sql: "select 1" });
    const body = JSON.parse(String((nlpFetch.mock.calls[0][1] as RequestInit).body));
    expect(body).toEqual({ question: "How many?", season: "2024-25" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ data: { answer: "nested" } }))
    );
    await expect(api.queryNlp("How many?")).resolves.toMatchObject({ answer: "nested" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({}, 400))
    );
    await expect(api.queryNlp("How many?")).rejects.toBeInstanceOf(ApiClientError);

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new DOMException("timed out", "TimeoutError");
      })
    );
    await expect(api.queryNlp("How many?")).rejects.toMatchObject({
      message: expect.stringContaining("timed out"),
    });
  });

  it("maps unknown errors", () => {
    expect(queryErrorMessage(new ApiClientError("nope", 400))).toBe("nope");
    expect(queryErrorMessage(new Error("boom"))).toBe("boom");
    expect(queryErrorMessage("weird")).toBe("Something went wrong. Try again in a moment.");
  });
});
