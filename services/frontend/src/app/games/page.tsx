"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";
import { api, queryErrorMessage } from "@/lib/api";
import { formatDate, formatSignedMargin } from "@/lib/format";
import { periodLabel } from "@/lib/game-flow";
import type { GameCollapse, LeagueGame } from "@/lib/types";

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
      <BiggestCollapses />
    </div>
  );
}

function BiggestCollapses() {
  const collapsesQuery = useQuery({
    queryKey: ["games", "collapses"],
    queryFn: () => api.listBiggestCollapses({ limit: 10 }),
  });
  const collapses = collapsesQuery.data?.data ?? [];

  return (
    <section className="space-y-2">
      <div>
        <p className="type-eyebrow">Collapse of the season</p>
        <h2 className="type-module">Biggest blown leads</h2>
        <p className="mt-1 text-sm text-ink-2">
          The largest lead a team held and still lost, from scoring play-by-play.
        </p>
      </div>
      {collapsesQuery.isLoading ? (
        <LoadingState label="Loading blown leads…" />
      ) : collapsesQuery.isError ? (
        <ErrorState message={queryErrorMessage(collapsesQuery.error)} />
      ) : collapses.length === 0 ? (
        <EmptyState message="No blown leads to show yet." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Blew it</th>
              <th>Lead</th>
              <th>Peaked</th>
              <th>Final</th>
              <th>PBP</th>
            </tr>
          </thead>
          <tbody>
            {collapses.map((collapse) => (
              <CollapseRow key={collapse.game_id} collapse={collapse} />
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function CollapseRow({ collapse }: { collapse: GameCollapse }) {
  const away = collapse.away_team_abbreviation ?? "Away";
  const home = collapse.home_team_abbreviation ?? "Home";
  const score =
    collapse.away_score != null && collapse.home_score != null
      ? `${away} ${collapse.away_score}–${home} ${collapse.home_score}`
      : "—";
  const peaked = collapse.blown_lead_period != null ? periodLabel(collapse.blown_lead_period) : "—";
  return (
    <tr>
      <td className="tabular whitespace-nowrap">{formatDate(collapse.game_date)}</td>
      <td className="font-semibold">{collapse.blown_lead_team_abbreviation ?? "—"}</td>
      <td className="tabular font-semibold">{collapse.largest_lead_blown}</td>
      <td className="tabular whitespace-nowrap">{peaked}</td>
      <td className="tabular whitespace-nowrap">{score}</td>
      <td>
        <Link href={`/games/${collapse.game_id}`} className="text-primary hover:underline">
          Play-by-play →
        </Link>
      </td>
    </tr>
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
