"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";
import { api, queryErrorMessage } from "@/lib/api";
import { formatDate, formatSignedMargin } from "@/lib/format";
import type { LeagueGame } from "@/lib/types";

export default function GamesPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading games…" />}>
      <GamesIndex />
    </Suspense>
  );
}

function GamesIndex() {
  const gamesQuery = useQuery({
    queryKey: ["games", "recent-finals"],
    queryFn: () => api.listGames({ limit: 15 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <p className="type-eyebrow">Recent final games</p>
        <h1 className="type-page">Game flow</h1>
        <p className="mt-1 text-sm text-ink-2">
          Scoring-play differential from play-by-play. Not live win probability.
        </p>
      </div>
      {gamesQuery.isLoading ? (
        <LoadingState label="Loading recent games…" />
      ) : gamesQuery.isError ? (
        <ErrorState message={queryErrorMessage(gamesQuery.error)} />
      ) : (gamesQuery.data?.data ?? []).length === 0 ? (
        <EmptyState message="No completed games to show yet." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Matchup</th>
              <th>Score</th>
              <th>Margin</th>
              <th>PBP</th>
            </tr>
          </thead>
          <tbody>
            {(gamesQuery.data?.data ?? []).map((game) => (
              <GameIndexRow key={game.game_id} game={game} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function GameIndexRow({ game }: { game: LeagueGame }) {
  const away = game.away_team_abbreviation ?? "Away";
  const home = game.home_team_abbreviation ?? "Home";
  const score =
    game.away_score != null && game.home_score != null
      ? `${game.away_score}–${game.home_score}`
      : "—";
  const margin = game.score_margin != null ? formatSignedMargin(game.score_margin) : "—";
  return (
    <tr>
      <td className="tabular whitespace-nowrap">{formatDate(game.game_date)}</td>
      <td>
        <span className="font-semibold">{away}</span>
        <span className="px-1 text-muted-foreground">at</span>
        <span className="font-semibold">{home}</span>
      </td>
      <td className="tabular font-semibold">{score}</td>
      <td className="tabular font-semibold">{margin}</td>
      <td>
        <Link href={`/games/${game.game_id}`} className="text-primary hover:underline">
          Play-by-play →
        </Link>
      </td>
    </tr>
  );
}
