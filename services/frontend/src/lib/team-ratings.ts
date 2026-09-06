import type { TeamSummary } from "@/lib/types";

export type TeamRatingPoint = {
  team_id: number;
  abbreviation: string;
  team_name: string;
  pts_scored_avg: number;
  pts_allowed_avg: number;
};

export function teamRatingPoints(teams: TeamSummary[]): TeamRatingPoint[] {
  return teams.flatMap((team) => {
    const scored = team.pts_scored_avg;
    const allowed = team.pts_allowed_avg;
    if (
      scored == null ||
      allowed == null ||
      !Number.isFinite(scored) ||
      !Number.isFinite(allowed)
    ) {
      return [];
    }
    return [
      {
        team_id: team.team_id,
        abbreviation: team.abbreviation,
        team_name: team.team_name,
        pts_scored_avg: scored,
        pts_allowed_avg: allowed,
      },
    ];
  });
}

export function leagueRatingAverages(points: TeamRatingPoint[]) {
  const n = points.length;
  if (n === 0) return null;
  return {
    pts_scored_avg: points.reduce((sum, point) => sum + point.pts_scored_avg, 0) / n,
    pts_allowed_avg: points.reduce((sum, point) => sum + point.pts_allowed_avg, 0) / n,
  };
}

export function paddedDomain(values: number[], pad = 2): [number, number] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 4);
  const extra = Math.max(pad, span * 0.12);
  return [min - extra, max + extra];
}
