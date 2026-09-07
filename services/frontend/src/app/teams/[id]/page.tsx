"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { CapPosition } from "@/components/teams/cap-position";
import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";
import { useSeason } from "@/hooks/use-season";
import { api, queryErrorMessage } from "@/lib/api";
import {
  formatDate,
  formatGamesBack,
  formatNumber,
  formatOrdinal,
  formatRecord,
  formatRecordWithWinPct,
  formatSignedMargin,
  teamCentricMargin,
} from "@/lib/format";
import { lastTenFromGames, streakFromGames } from "@/lib/team-form";
import type { TeamGame } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TeamProfilePage() {
  return (
    <Suspense fallback={<LoadingState label="Loading team…" />}>
      <TeamProfile />
    </Suspense>
  );
}

function TeamProfile() {
  const params = useParams<{ id: string }>();
  const teamId = params.id;
  const { season: requestedSeason, seasons } = useSeason();
  const [seasonOverride, setSeasonOverride] = useState<string | null>(null);
  const [sinceSeason, setSinceSeason] = useState("");
  const [opponentId, setOpponentId] = useState("");
  const [arenaCity, setArenaCity] = useState("");
  const [location, setLocation] = useState<"all" | "home" | "away">("all");
  const season = seasonOverride ?? requestedSeason;

  const teamQuery = useQuery({
    queryKey: ["team", teamId],
    queryFn: () => api.getTeam(teamId),
    enabled: Boolean(teamId),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.listTeams(),
  });

  const recordParams = {
    season: season || undefined,
    since_season: sinceSeason || undefined,
    opponent_team_id: opponentId || undefined,
    location: location === "all" ? undefined : location,
    arena_city: arenaCity || undefined,
  };

  const gamesQuery = useQuery({
    queryKey: ["team", teamId, "games", recordParams],
    queryFn: () => api.getTeamGames(teamId, { ...recordParams, limit: 200 }),
    enabled: Boolean(teamId),
  });
  const overallQuery = useQuery({
    queryKey: ["team", teamId, "record", "overall", recordParams],
    queryFn: () => api.getTeamRecord(teamId, recordParams),
    enabled: Boolean(teamId),
  });
  const homeQuery = useQuery({
    queryKey: ["team", teamId, "record", "home", recordParams],
    queryFn: () => api.getTeamRecord(teamId, { ...recordParams, location: "home" }),
    enabled: Boolean(teamId),
  });
  const awayQuery = useQuery({
    queryKey: ["team", teamId, "record", "away", recordParams],
    queryFn: () => api.getTeamRecord(teamId, { ...recordParams, location: "away" }),
    enabled: Boolean(teamId),
  });

  const team = teamQuery.data;
  const standing = team?.standing;
  const headerSeason = team?.record_season;
  const needsForm = Boolean(headerSeason && (!standing?.last_10 || !standing?.streak));
  const formQuery = useQuery({
    queryKey: ["team", teamId, "form", headerSeason],
    queryFn: () =>
      api.getTeamGames(teamId, {
        season: headerSeason ?? undefined,
        season_type: "Regular Season",
        limit: 10,
      }),
    enabled: Boolean(teamId) && needsForm,
  });

  const games = gamesQuery.data?.data ?? [];
  const overall = overallQuery.data;

  if (!teamId) {
    return <ErrorState message="Invalid team id." />;
  }

  if (teamQuery.isLoading) {
    return <LoadingState label="Loading team…" />;
  }

  if (teamQuery.isError || !team) {
    return (
      <ErrorState
        message={teamQuery.error ? queryErrorMessage(teamQuery.error) : "Team not found."}
      />
    );
  }

  const headerRecord = team.season_record;
  const opponents = (teamsQuery.data?.data ?? []).filter((item) => item.team_id !== teamId);
  const arenaCities = [
    ...new Set(
      (teamsQuery.data?.data ?? [])
        .map((item) => item.city)
        .filter((city): city is string => Boolean(city))
    ),
  ].sort();
  const last10 = standing?.last_10 || lastTenFromGames(formQuery.data?.data ?? []);
  const streak = standing?.streak || streakFromGames(formQuery.data?.data ?? []);
  const gamesTotal = gamesQuery.data?.meta.total ?? games.length;
  const rankLine =
    standing?.conference_rank != null
      ? `${formatOrdinal(standing.conference_rank)} in ${standing.conference}`
      : null;
  const gamesBack = formatGamesBack(standing?.games_back);
  const rsSubline = [
    headerRecord?.games != null ? `${headerRecord.games} games` : null,
    rankLine,
    gamesBack !== "—" ? gamesBack : null,
  ]
    .filter(Boolean)
    .join(" · ");

  function resetFilters() {
    setSeasonOverride(null);
    setSinceSeason("");
    setOpponentId("");
    setArenaCity("");
    setLocation("all");
  }

  // TeamRecord.games is optional; a missing count reads as zero so the KPI hides.
  const playInGames = team.play_in_record?.games ?? 0;
  const playoffGames = team.playoff_record?.games ?? 0;

  return (
    <div className="space-y-8">
      <p className="text-xs text-muted-foreground">
        <Link href="/teams" className="hover:text-foreground">
          Teams
        </Link>
        {" / "}
        {team.team_name}
      </p>

      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 className="type-entity">{team.team_name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {[
              team.abbreviation,
              team.conference,
              team.division,
              [team.arena_name, team.city].filter(Boolean).join(", ") || null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <dl
          data-testid="team-season-kpis"
          className="flex flex-wrap items-start justify-end gap-x-2 gap-y-4"
        >
          <SeasonKpi
            testId="team-kpi-regular-season"
            label={`${headerSeason || "Season"} Regular Season`}
            value={
              headerRecord
                ? formatRecordWithWinPct(
                    headerRecord.wins,
                    headerRecord.losses,
                    headerRecord.win_pct
                  )
                : "—"
            }
            subtext={rsSubline}
          />
          {team.play_in_record && playInGames > 0 ? (
            <SeasonKpi
              testId="team-kpi-play-in"
              label="Play-in"
              value={formatRecord(team.play_in_record.wins, team.play_in_record.losses)}
              subtext={`${playInGames} GP`}
            />
          ) : null}
          {team.playoff_record && playoffGames > 0 ? (
            <SeasonKpi
              testId="team-kpi-playoffs"
              label="Playoffs"
              value={formatRecord(team.playoff_record.wins, team.playoff_record.losses)}
              subtext={`${playoffGames} GP`}
            />
          ) : null}
          <SeasonKpi
            testId="team-kpi-last-10"
            label="Last 10"
            value={last10 ?? "—"}
            subtext={streak ? `Streak ${streak}` : null}
          />
        </dl>
      </div>

      <CapPosition team={team} />

      <div className="flex flex-wrap items-end gap-3 border-y border-border py-3">
        <p className="mr-2 type-eyebrow">Filter games</p>
        <LabeledSelect
          label="Since"
          value={sinceSeason}
          onChange={setSinceSeason}
          options={[
            { value: "", label: "—" },
            ...seasons.map((item) => ({ value: item, label: item })),
          ]}
        />
        <LabeledSelect
          label="Opponent"
          value={opponentId}
          onChange={setOpponentId}
          options={[
            { value: "", label: "Any" },
            ...opponents.map((item) => ({ value: String(item.team_id), label: item.abbreviation })),
          ]}
        />
        <LabeledSelect
          label="Arena city"
          value={arenaCity}
          onChange={setArenaCity}
          options={[
            { value: "", label: "Any" },
            ...arenaCities.map((city) => ({ value: city, label: city })),
          ]}
        />
        <div className="flex border border-input">
          {(["all", "home", "away"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setLocation(value)}
              className={cn("seg-btn", location === value && "seg-btn-active")}
            >
              {value}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="h-8 px-2 text-sm text-muted-foreground hover:text-foreground"
          onClick={resetFilters}
        >
          Reset
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <section>
          <h2 className="type-module">
            Games
            {gamesTotal ? ` ${formatNumber(gamesTotal)} games` : ""}
            {overall
              ? ` · ${formatRecordWithWinPct(overall.wins, overall.losses, overall.win_pct)}`
              : " · —"}
          </h2>
          {gamesQuery.isLoading ? (
            <LoadingState label="Loading games…" />
          ) : gamesQuery.isError ? (
            <ErrorState message={queryErrorMessage(gamesQuery.error)} />
          ) : games.length === 0 ? (
            <EmptyState message="No games match these filters." />
          ) : (
            <table className="data-table mt-3">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Opp</th>
                  <th>Res</th>
                  <th className="text-right">Score</th>
                  <th className="text-right">Margin</th>
                  <th>Arena</th>
                </tr>
              </thead>
              <tbody>
                {games.map((game) => {
                  const view = normalizeTeamGame(game, teamId);
                  return (
                    <tr key={game.game_id}>
                      <td className="tabular">{formatDate(view.game_date)}</td>
                      <td className="font-semibold">{view.opponent}</td>
                      <td
                        className={cn(
                          "font-medium",
                          view.result === "W" && "text-primary",
                          view.result === "L" && "text-destructive"
                        )}
                      >
                        {view.result ?? "—"}
                      </td>
                      <td className="tabular text-right">
                        {view.teamScore != null && view.oppScore != null
                          ? `${view.teamScore}–${view.oppScore}`
                          : "—"}
                      </td>
                      <td className="tabular text-right">{formatSignedMargin(view.margin)}</td>
                      <td className="text-muted-foreground">{view.arena}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>

        <aside>
          <div className="border border-border p-4">
            <h2 className="type-module">Split under this filter</h2>
            <div className="mt-4 space-y-3">
              <RecordBar
                label="Filtered games"
                wins={overall?.wins ?? 0}
                losses={overall?.losses ?? 0}
              />
              <RecordBar
                label="Home"
                wins={homeQuery.data?.wins ?? 0}
                losses={homeQuery.data?.losses ?? 0}
              />
              <RecordBar
                label="Away"
                wins={awayQuery.data?.wins ?? 0}
                losses={awayQuery.data?.losses ?? 0}
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function SeasonKpi({
  label,
  value,
  subtext,
  testId,
}: {
  label: string;
  value: string;
  subtext?: string | null;
  testId: string;
}) {
  return (
    <div
      data-testid={testId}
      className="min-w-[7.5rem] border-l border-border px-4 first:border-l-0 first:pl-0"
    >
      <dt className="text-[11px] tracking-wide text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-1 type-hero-stat tabular">{value}</dd>
      {subtext ? <p className="mt-1 text-xs text-muted-foreground">{subtext}</p> : null}
    </div>
  );
}

function LabeledSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="text-xs text-muted-foreground">
      {label}
      <select
        className={cn("field mt-1 block", value && "field-query")}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value || option.label} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function RecordBar({ label, wins, losses }: { label: string; wins: number; losses: number }) {
  const total = wins + losses;
  const pct = total ? wins / total : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span>{label}</span>
        <span className="tabular text-muted-foreground">
          {formatRecordWithWinPct(wins, losses, total ? pct : null)}
        </span>
      </div>
      <div className="flex h-2 bg-skel-1">
        <div className="bg-primary" style={{ width: `${pct * 100}%` }} />
        <div className="bg-loss-bar" style={{ width: `${(1 - pct) * 100}%` }} />
      </div>
    </div>
  );
}

function normalizeTeamGame(game: TeamGame, teamId: string) {
  const isHome = game.location?.toLowerCase() === "home" || game.home_team_id === teamId;
  const opponent =
    game.opponent_abbreviation ??
    (isHome ? game.away_team_abbreviation : game.home_team_abbreviation) ??
    "—";
  const teamScore = isHome
    ? (game.home_score ?? game.team_score)
    : (game.away_score ?? game.team_score);
  const oppScore = isHome
    ? (game.away_score ?? game.opponent_score)
    : (game.home_score ?? game.opponent_score);
  const result =
    game.result ??
    (game.is_win == null ? null : game.is_win ? "W" : "L") ??
    (teamScore != null && oppScore != null ? (teamScore > oppScore ? "W" : "L") : null);
  const margin = teamCentricMargin(teamScore, oppScore, game.score_margin, game.is_win);
  return {
    season: game.season,
    game_date: game.game_date,
    opponent,
    result,
    teamScore,
    oppScore,
    margin,
    arena: game.arena ?? game.arena_city ?? "—",
  };
}
