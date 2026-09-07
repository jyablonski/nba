"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";
import { useDebounce } from "@/hooks/use-debounce";
import { useSeason } from "@/hooks/use-season";
import { api, queryErrorMessage } from "@/lib/api";
import { formatNumber, formatStat } from "@/lib/format";
import { withSeason } from "@/lib/nav";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

export default function PlayersPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading players…" />}>
      <PlayersDirectory />
    </Suspense>
  );
}

function PlayersDirectory() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { season } = useSeason();
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [activeOnly, setActiveOnly] = useState(true);
  const [teamId, setTeamId] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const debounced = useDebounce(search, 300);

  const togglePlayer = useCallback((playerId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(playerId)) next.delete(playerId);
      else next.add(playerId);
      return next;
    });
  }, []);

  useEffect(() => {
    const next = debounced.trim();
    const current = searchParams.get("search") ?? "";
    if (next === current) return;
    const params = new URLSearchParams(searchParams.toString());
    if (next) params.set("search", next);
    else params.delete("search");
    router.replace(params.toString() ? `/players?${params}` : "/players");
  }, [debounced, router, searchParams]);

  const playersQuery = useQuery({
    queryKey: ["players", debounced, activeOnly, teamId, page],
    queryFn: () =>
      api.searchPlayers(debounced.trim(), {
        active: activeOnly ? true : undefined,
        team_id: teamId || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.listTeams(),
  });

  const players = playersQuery.data?.data ?? [];
  const teamOptions = [...(teamsQuery.data?.data ?? [])].sort((a, b) =>
    a.abbreviation.localeCompare(b.abbreviation)
  );
  const total = playersQuery.data?.meta.total ?? 0;
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min(total, (page + 1) * PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="type-page">Players</h1>
        <p className="mt-1 text-sm text-ink-2">
          {formatNumber(total)} in directory. Career averages come from game logs.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          placeholder="Search players"
          className={cn("field w-48", search.trim() && "field-query")}
        />
        {search.trim() ? (
          <span className="border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">
            fuzzy
          </span>
        ) : null}
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={activeOnly}
            onCheckedChange={(checked) => {
              setActiveOnly(checked);
              setPage(0);
            }}
          />
          Active only
        </label>
        <select
          className={cn("field", teamId && "field-query")}
          value={teamId}
          onChange={(event) => {
            setTeamId(event.target.value);
            setPage(0);
          }}
        >
          <option value="">Team All</option>
          {teamOptions.map((team) => (
            <option key={team.team_id} value={team.team_id}>
              {team.abbreviation}
            </option>
          ))}
        </select>
        <div className="ml-auto flex items-center gap-3">
          {selected.size > 0 ? (
            <span className="text-sm text-muted-foreground">{selected.size} selected</span>
          ) : null}
          <button
            type="button"
            disabled={selected.size < 2}
            onClick={() =>
              router.push(withSeason(`/players/compare?ids=${[...selected].join(",")}`, season))
            }
            className="btn-fill"
          >
            Compare selected →
          </button>
        </div>
      </div>

      {playersQuery.isLoading ? (
        <LoadingState label="Searching players…" />
      ) : playersQuery.isError ? (
        <ErrorState message={queryErrorMessage(playersQuery.error)} />
      ) : players.length === 0 ? (
        <EmptyState
          title={debounced ? "No players match" : "No players yet"}
          message={debounced ? "Try a different name." : "Nothing to show yet."}
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th className="w-8" />
                <th>Name</th>
                <th>Team</th>
                <th>Pos</th>
                <th className="text-right">GP</th>
                <th className="text-right">PPG</th>
                <th className="text-right">RPG</th>
                <th className="text-right">APG</th>
                <th className="pl-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {players.map((player) => (
                <tr
                  key={player.player_id}
                  className={selected.has(player.player_id) ? "bg-row-selected" : undefined}
                >
                  <td>
                    <Checkbox
                      checked={selected.has(player.player_id)}
                      onCheckedChange={() => togglePlayer(player.player_id)}
                    />
                  </td>
                  <td>
                    <Link
                      href={`/players/${player.player_id}`}
                      className="text-primary hover:underline"
                    >
                      {player.full_name}
                    </Link>
                  </td>
                  <td className="font-semibold">{player.team_abbreviation ?? "—"}</td>
                  <td>{player.position ?? "—"}</td>
                  <td className="tabular text-right">{formatNumber(player.career_games_played)}</td>
                  <td className="tabular text-right">{formatStat(player.career_ppg)}</td>
                  <td className="tabular text-right">{formatStat(player.career_rpg)}</td>
                  <td className="tabular text-right">{formatStat(player.career_apg)}</td>
                  <td className="pl-4 text-muted-foreground">
                    {player.is_active ? "Active" : "Inactive"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > 0 ? (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted-foreground">
            {from}–{to} of {formatNumber(total)} matches
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              className="btn-ghost"
            >
              ← Prev
            </button>
            <button
              type="button"
              disabled={to >= total}
              onClick={() => setPage((current) => current + 1)}
              className="btn-ghost"
            >
              Next →
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
