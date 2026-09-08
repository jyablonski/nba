import { describe, expect, it } from "vitest";

import { leagueRatingAverages, paddedDomain, teamRatingPoints } from "@/lib/team-ratings";
import type { TeamSummary } from "@/lib/types";

const TEAM_A = "00000000-0000-4000-8000-000000000201";
const TEAM_B = "00000000-0000-4000-8000-000000000202";
const TEAM_C = "00000000-0000-4000-8000-000000000203";

function team(partial: Partial<TeamSummary> & Pick<TeamSummary, "team_id">): TeamSummary {
  return {
    abbreviation: "BOS",
    team_name: "Boston Celtics",
    conference: "East",
    division: "Atlantic",
    ...partial,
  };
}

describe("team ratings", () => {
  it("keeps only teams with finite Regular Season scoring averages", () => {
    expect(
      teamRatingPoints([
        team({ team_id: TEAM_A, pts_scored_avg: 116.4, pts_allowed_avg: 109.2 }),
        team({ team_id: TEAM_B, abbreviation: "NYK", pts_scored_avg: null, pts_allowed_avg: 110 }),
        team({
          team_id: TEAM_C,
          abbreviation: "BKN",
          pts_scored_avg: Number.NaN,
          pts_allowed_avg: 112,
        }),
      ])
    ).toEqual([
      {
        team_id: TEAM_A,
        abbreviation: "BOS",
        team_name: "Boston Celtics",
        pts_scored_avg: 116.4,
        pts_allowed_avg: 109.2,
      },
    ]);
  });

  it("averages plotted teams for the quadrant lines", () => {
    expect(
      leagueRatingAverages([
        {
          team_id: TEAM_A,
          abbreviation: "BOS",
          team_name: "Boston Celtics",
          pts_scored_avg: 110,
          pts_allowed_avg: 100,
        },
        {
          team_id: TEAM_B,
          abbreviation: "NYK",
          team_name: "New York Knicks",
          pts_scored_avg: 120,
          pts_allowed_avg: 110,
        },
      ])
    ).toEqual({ pts_scored_avg: 115, pts_allowed_avg: 105 });
    expect(leagueRatingAverages([])).toBeNull();
  });

  it("pads the axis domain so logos are not clipped", () => {
    const [min, max] = paddedDomain([110, 118]);
    expect(min).toBeLessThan(110);
    expect(max).toBeGreaterThan(118);
  });
});
