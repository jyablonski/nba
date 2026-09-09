import { expect, type Page } from "@playwright/test";

export const PRIMARY_NAV = [
  "Home",
  "Schedule",
  "Players",
  "Teams",
  "Compare",
  "Ask",
  "About",
] as const;

export type MockApiOptions = {
  empty?: boolean;
};

export async function mockApi(page: Page, options: MockApiOptions = {}) {
  await page.addInitScript((opts: MockApiOptions) => {
    const empty = Boolean(opts.empty);
    const json = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      });

    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input instanceof Request ? input.url : input);
      if (!url.includes("/api/v1/")) {
        return originalFetch(input, init);
      }

      if (url.includes("/query")) {
        return json({
          answer: "Kawhi Leonard has 12 back-to-back sets",
          data: [],
          sql: "gold.fct_player_game_logs",
        });
      }

      if (url.includes("/status")) {
        return json({
          data: empty
            ? {
                last_scraped_at: null,
                player_count: 0,
                game_count: 0,
                season_count: 0,
                first_season: "2010-11",
                last_season: null,
              }
            : {
                last_scraped_at: "2026-09-04T04:12:00Z",
                player_count: 2314,
                game_count: 20486,
                season_count: 16,
                first_season: "2010-11",
                last_season: "2025-26",
              },
        });
      }

      if (url.includes("/season-stats")) {
        return json({
          data: empty
            ? []
            : [
                {
                  player_id: "00000000-0000-4000-8000-000000202695",
                  season: "2025-26",
                  games_played: 74,
                  ppg: 23.4,
                  rpg: 6.1,
                  apg: 3.2,
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 50, offset: 0 },
        });
      }

      if (url.includes("/game-log")) {
        return json({
          data: empty
            ? []
            : [
                {
                  game_date: "2025-10-22",
                  opponent_abbreviation: "GSW",
                  location: "home",
                  result: "W",
                  minutes: 36.5,
                  points: 28,
                  rebounds: 8,
                  assists: 6,
                  is_back_to_back: false,
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 500, offset: 0 },
        });
      }

      if (url.includes("/back-to-backs")) {
        return json({
          data: {
            player_id: "00000000-0000-4000-8000-000000202695",
            player_name: "Kawhi Leonard",
            total_back_to_backs: 12,
            games_played_in_b2b: 10,
            avg_pts_b2b: 24.1,
            avg_pts_non_b2b: 26.4,
          },
        });
      }

      if (url.includes("/players/compare/head-to-head")) {
        return json({
          data: {
            games_played: 0,
            players: [],
            games: [],
          },
        });
      }

      if (url.includes("/players/compare")) {
        return json({
          data: empty
            ? []
            : [
                {
                  player_id: "00000000-0000-4000-8000-000000202695",
                  full_name: "Kawhi Leonard",
                  team_abbreviation: "LAC",
                  position: "F",
                  career_games_played: 700,
                  seasons_played: 12,
                  first_season: "2011-12",
                  last_season: "2024-25",
                  career_ppg: 19.2,
                  career_rpg: 6.4,
                  career_apg: 3.0,
                },
                {
                  player_id: "00000000-0000-4000-8000-000000201939",
                  full_name: "Stephen Curry",
                  team_abbreviation: "GSW",
                  position: "G",
                  career_games_played: 1000,
                  seasons_played: 16,
                  first_season: "2009-10",
                  last_season: "2024-25",
                  career_ppg: 24.6,
                  career_rpg: 4.7,
                  career_apg: 6.4,
                },
              ],
          meta: { total: empty ? 0 : 2, limit: 2, offset: 0 },
        });
      }

      // Player ids are UUIDs since the provider-independent identity migration.
      const playerMatch = url.match(/\/players\/([0-9a-f-]{36})/i);
      if (playerMatch) {
        const playerId = playerMatch[1];
        const curry = playerId === "00000000-0000-4000-8000-000000201939";
        return json({
          data: {
            player_id: playerId,
            full_name: curry ? "Stephen Curry" : "Kawhi Leonard",
            position: curry ? "G" : "F",
            team_abbreviation: curry ? "GSW" : "LAC",
            is_active: true,
            first_name: curry ? "Stephen" : "Kawhi",
            last_name: curry ? "Curry" : "Leonard",
            career_games_played: curry ? 1000 : 700,
            seasons_played: curry ? 16 : 12,
            first_season: curry ? "2009-10" : "2011-12",
            last_season: "2024-25",
            career_ppg: curry ? 24.6 : 19.2,
            career_rpg: curry ? 4.7 : 6.4,
            career_apg: curry ? 6.4 : 3.0,
            current_season_salary: curry ? 55761217 : 45000000,
            current_remaining_guaranteed: curry ? 101000000 : 90000000,
            current_contract_season: "2024-25",
          },
        });
      }

      if (url.includes("/players")) {
        return json({
          data: empty
            ? []
            : [
                {
                  player_id: "00000000-0000-4000-8000-000000202695",
                  full_name: "Kawhi Leonard",
                  position: "F",
                  team_abbreviation: "LAC",
                  is_active: true,
                  career_games_played: 700,
                  career_ppg: 19.2,
                },
                {
                  player_id: "00000000-0000-4000-8000-000000201939",
                  full_name: "Stephen Curry",
                  position: "G",
                  team_abbreviation: "GSW",
                  is_active: true,
                  career_games_played: 1000,
                  career_ppg: 24.6,
                },
              ],
          meta: { total: empty ? 0 : 2, limit: 25, offset: 0 },
        });
      }

      if (url.includes("/teams/") && url.includes("/games")) {
        return json({
          data: empty
            ? []
            : [
                {
                  game_id: "0022400001",
                  season: "2025-26",
                  game_date: "2024-10-22",
                  location: "away",
                  opponent_abbreviation: "CHI",
                  team_score: 118,
                  opponent_score: 110,
                  is_win: true,
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 82, offset: 0 },
        });
      }

      if (url.includes("/teams/") && url.includes("/record")) {
        return json({
          data: {
            team_id: 1610612744,
            team_name: "Golden State Warriors",
            wins: 10,
            losses: 5,
            win_pct: 0.667,
            games: 15,
          },
        });
      }

      if (/\/teams\/\d+/.test(url)) {
        return json({
          data: {
            team_id: 1610612744,
            abbreviation: "GSW",
            team_name: "Golden State Warriors",
            conference: "West",
            division: "Pacific",
            city: "San Francisco",
            nickname: "Warriors",
            arena_name: "Chase Center",
            arena_latitude: 37.76806,
            arena_longitude: -122.3875,
            current_season_payroll: 51000000,
            current_remaining_guaranteed: 120000000,
            current_contract_season: "2024-25",
            record_season: "2025-26",
            season_record: { wins: 50, losses: 32, win_pct: 0.61, games: 82 },
            play_in_record: { wins: 1, losses: 0, win_pct: 1, games: 1 },
            playoff_record: { wins: 4, losses: 4, win_pct: 0.5, games: 8 },
            luxury_tax: 170814000,
            first_apron: 178132000,
            second_apron: 188931000,
            over_luxury_tax: false,
            over_first_apron: false,
            over_second_apron: false,
            standing: {
              season: "2025-26",
              conference: "West",
              conference_rank: 1,
              wins: 50,
              losses: 32,
              games_back: 0,
            },
          },
        });
      }

      if (url.includes("/teams")) {
        return json({
          data: empty
            ? []
            : [
                {
                  team_id: 1610612744,
                  abbreviation: "GSW",
                  team_name: "Golden State Warriors",
                  conference: "West",
                  division: "Pacific",
                  city: "San Francisco",
                  nickname: "Warriors",
                  wins: 50,
                  losses: 32,
                  win_pct: 0.61,
                  pts_scored_avg: 114.8,
                  pts_allowed_avg: 112.1,
                },
                {
                  team_id: 1610612738,
                  abbreviation: "BOS",
                  team_name: "Boston Celtics",
                  conference: "East",
                  division: "Atlantic",
                  city: "Boston",
                  nickname: "Celtics",
                  wins: 61,
                  losses: 21,
                  win_pct: 0.744,
                  pts_scored_avg: 116.4,
                  pts_allowed_avg: 109.2,
                },
              ],
          meta: { total: empty ? 0 : 2, limit: 50, offset: 0 },
        });
      }

      if (url.includes("/standings")) {
        return json({
          data: empty
            ? []
            : [
                {
                  team_id: 1610612744,
                  abbreviation: "GSW",
                  team_name: "Golden State Warriors",
                  season: "2025-26",
                  season_type: "Regular Season",
                  as_of_date: "2025-04-13",
                  conference: "West",
                  division: "Pacific",
                  conference_rank: 1,
                  division_rank: 1,
                  wins: 50,
                  losses: 32,
                  win_pct: 0.61,
                  games_back: 0,
                  conf_games_back: 0,
                  streak: "W5",
                  last_10: "8-2",
                },
                {
                  team_id: 1610612741,
                  abbreviation: "CHI",
                  team_name: "Chicago Bulls",
                  season: "2025-26",
                  season_type: "Regular Season",
                  as_of_date: "2025-04-13",
                  conference: "East",
                  division: "Central",
                  conference_rank: 5,
                  division_rank: 2,
                  wins: 45,
                  losses: 37,
                  win_pct: 0.549,
                  games_back: 4,
                  conf_games_back: 4,
                  streak: "W2",
                  last_10: "5-5",
                },
              ],
          meta: { total: empty ? 0 : 2, limit: 50, offset: 0 },
        });
      }

      if (url.includes("/seasons")) {
        return json({
          data: empty ? [] : [{ season: "2025-26" }, { season: "2024-25" }],
          meta: { total: empty ? 0 : 2, limit: 2, offset: 0 },
        });
      }

      if (url.includes("/schedule")) {
        return json({
          data: empty
            ? []
            : [
                {
                  game_id: "0022500999",
                  season: "2025-26",
                  game_date: "2026-10-22",
                  status: "Scheduled",
                  home_team_id: 1610612744,
                  away_team_id: 1610612747,
                  home_team_abbreviation: "GSW",
                  away_team_abbreviation: "LAL",
                  arena: "Chase Center",
                  arena_city: "San Francisco",
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 50, offset: 0 },
        });
      }

      if (url.includes("/games/0022400002/play-by-play")) {
        const events = [
          { period: 1, elapsed_seconds: 120, score_home: 2, score_away: 12 },
          { period: 2, elapsed_seconds: 900, score_home: 40, score_away: 61 },
          { period: 3, elapsed_seconds: 1900, score_home: 78, score_away: 90 },
          { period: 4, elapsed_seconds: 2700, score_home: 112, score_away: 113 },
          { period: 4, elapsed_seconds: 2870, score_home: 118, score_away: 115 },
        ].map((event, index) => ({
          game_id: "0022400002",
          action_number: index + 1,
          clock: null,
          ...event,
          score_differential: event.score_home - event.score_away,
        }));
        return json({ data: events, meta: { total: events.length, limit: 0, offset: 0 } });
      }

      if (url.includes("/play-by-play")) {
        return json({ data: [], meta: { total: 0, limit: 0, offset: 0 } });
      }

      // The comeback game the collapse table links to.
      if (url.includes("/games/0022400002/flow")) {
        return json({
          data: {
            game_id: "0022400002",
            season: "2025-26",
            game_date: "2024-11-02",
            home_team_abbreviation: "BOS",
            away_team_abbreviation: "MIA",
            home_score: 118,
            away_score: 115,
            winning_team_abbreviation: "BOS",
            has_play_by_play: true,
            scoring_play_count: 97,
            max_lead: 21,
            lead_changes: 4,
            ties: 3,
            home_lead_pct: 0.18,
            away_lead_pct: 0.74,
            tied_pct: 0.08,
            largest_lead_blown: 21,
            blown_lead_team_abbreviation: "MIA",
            comeback_team_abbreviation: "BOS",
            blown_lead_period: 3,
            winner_margin_entering_fourth: -9,
            is_wire_to_wire: false,
            overtime_periods: 0,
          },
        });
      }

      if (url.includes("/flow")) {
        return json({
          data: {
            game_id: "0022400001",
            season: "2025-26",
            game_date: "2024-10-22",
            home_team_id: 1610612744,
            away_team_id: 1610612747,
            home_team_abbreviation: "GSW",
            away_team_abbreviation: "LAL",
            has_play_by_play: false,
          },
        });
      }

      // Must precede the generic /games branch.
      if (url.includes("/games/collapses")) {
        return json({
          data: empty
            ? []
            : [
                {
                  game_id: "0022400002",
                  season: "2025-26",
                  game_date: "2024-11-02",
                  home_team_abbreviation: "BOS",
                  away_team_abbreviation: "MIA",
                  home_score: 118,
                  away_score: 115,
                  largest_lead_blown: 21,
                  blown_lead_team_abbreviation: "MIA",
                  comeback_team_abbreviation: "BOS",
                  blown_lead_period: 3,
                  winner_margin_entering_fourth: -9,
                  lead_changes: 4,
                  overtime_periods: 0,
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 10, offset: 0 },
        });
      }

      if (url.includes("/games")) {
        return json({
          data: empty
            ? []
            : [
                {
                  game_id: "0022400001",
                  season: "2025-26",
                  season_type: "Regular Season",
                  game_date: "2024-10-22",
                  home_team_id: 1610612744,
                  away_team_id: 1610612747,
                  home_team_abbreviation: "GSW",
                  away_team_abbreviation: "LAL",
                  home_score: 120,
                  away_score: 110,
                  score_margin: 10,
                  arena_city: "San Francisco",
                },
              ],
          meta: { total: empty ? 0 : 1, limit: 10, offset: 0 },
        });
      }

      return json({ data: [] });
    };
  }, options);
}

export function primaryNav(page: Page) {
  return page.getByRole("navigation", { name: "Primary" });
}

export async function expectPrimaryNav(page: Page) {
  const nav = primaryNav(page);
  for (const label of PRIMARY_NAV) {
    await expect(nav.getByRole("link", { name: label })).toBeVisible();
  }
}

export async function expectNo2010Range(page: Page) {
  await expect(page.getByText(/2010-11/)).toHaveCount(0);
  await expect(page.getByText(/since 2010-11/i)).toHaveCount(0);
}
