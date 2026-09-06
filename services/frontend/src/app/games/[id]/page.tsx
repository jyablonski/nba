"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { GameFlowChart } from "@/components/charts/game-flow-chart";
import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";
import { api, queryErrorMessage } from "@/lib/api";
import { formatLeadShare, formatMatchupTitle } from "@/lib/game-flow";
import { formatDate, formatNumber, formatSignedMargin } from "@/lib/format";
import type { GameFlow } from "@/lib/types";

export default function GameFlowPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading game flow…" />}>
      <GameFlowBody />
    </Suspense>
  );
}

function GameFlowBody() {
  const params = useParams<{ id: string }>();
  const gameId = String(params.id ?? "");

  const flowQuery = useQuery({
    queryKey: ["game-flow", gameId],
    queryFn: () => api.getGameFlow(gameId),
    enabled: Boolean(gameId),
  });
  const pbpQuery = useQuery({
    queryKey: ["game-pbp", gameId],
    queryFn: () => api.getGamePlayByPlay(gameId),
    enabled: Boolean(gameId),
  });

  const flow = flowQuery.data;
  const events = pbpQuery.data?.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <p className="type-eyebrow">
          {flow ? formatDate(flow.game_date) : "Game flow"}
          {flow?.season ? ` · ${flow.season}` : ""}
        </p>
        <h1 className="type-page text-center sm:text-left">
          {flow ? formatMatchupTitle(flow) : "Game flow"}
        </h1>
      </div>

      {flowQuery.isLoading || pbpQuery.isLoading ? (
        <LoadingState label="Loading play-by-play…" />
      ) : flowQuery.isError ? (
        <ErrorState message={queryErrorMessage(flowQuery.error)} />
      ) : pbpQuery.isError ? (
        <ErrorState message={queryErrorMessage(pbpQuery.error)} />
      ) : !flow ? (
        <EmptyState message="Game not found." />
      ) : !flow.has_play_by_play || events.length === 0 ? (
        <EmptyState
          title="No play-by-play data available."
          message="There's no scoring timeline for this game."
        />
      ) : (
        <>
          <FlowFacts flow={flow} />
          <GameFlowChart events={events} flow={flow} />
        </>
      )}

      <p className="text-sm">
        <Link href="/games" className="text-primary hover:underline">
          All recent final games →
        </Link>
      </p>
    </div>
  );
}

function FlowFacts({ flow }: { flow: GameFlow }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="border border-rule bg-accent-soft px-2 py-1 text-foreground">
        {formatLeadShare("home", flow.home_team_abbreviation, flow.home_lead_pct)}
      </span>
      <span className="border border-rule bg-tint px-2 py-1 text-foreground">
        {formatLeadShare("away", flow.away_team_abbreviation, flow.away_lead_pct)}
      </span>
      <span className="text-ink-2">Max lead {formatSignedMargin(flow.max_lead)}</span>
      <span className="text-ink-2">{formatNumber(flow.lead_changes)} lead changes</span>
      <span className="text-ink-2">{formatNumber(flow.ties)} ties</span>
      <span className="text-ink-2">{formatNumber(flow.scoring_play_count)} plays</span>
    </div>
  );
}
