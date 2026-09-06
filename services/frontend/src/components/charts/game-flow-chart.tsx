"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/query-state";
import {
  formatBiggestRunCaption,
  formatFlowTooltipLabel,
  formatFlowTooltipPlay,
  formatFlowTooltipScore,
  periodLabel,
  quarterAxisTicks,
  selectBiggestRun,
} from "@/lib/game-flow";
import {
  colorForLeader,
  leadSegments,
  leaderFromDifferential,
  resolvePlotColors,
} from "@/lib/team-colors";
import type { GameFlow, PlayByPlayEvent } from "@/lib/types";

const tooltipStyle = {
  background: "#FBFAF5",
  border: "1px solid #D8D3C6",
  borderRadius: 0,
  color: "#1A1A1A",
  margin: 0,
  padding: "10px",
  whiteSpace: "nowrap" as const,
};

export function GameFlowTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: ChartPoint; value?: unknown }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  const play = formatFlowTooltipPlay(point);
  return (
    <div className="recharts-default-tooltip" style={tooltipStyle}>
      <p className="recharts-tooltip-label" style={{ margin: 0 }}>
        {formatFlowTooltipLabel(point)}
      </p>
      <p className="recharts-tooltip-item" style={{ margin: 0, paddingTop: 4, paddingBottom: 4 }}>
        <span className="recharts-tooltip-item-name">Score</span>
        <span className="recharts-tooltip-item-separator"> : </span>
        <span className="recharts-tooltip-item-value">
          {formatFlowTooltipScore(point.score_differential, point)}
        </span>
      </p>
      {play ? (
        <p className="recharts-tooltip-item" style={{ margin: 0, paddingTop: 4, paddingBottom: 4 }}>
          {play}
        </p>
      ) : null}
    </div>
  );
}

type ChartPoint = {
  elapsed_seconds: number;
  score_differential: number;
  score_home: number;
  score_away: number;
  period: number | null;
  clock: string | null;
  clock_remaining_seconds: number | null;
  scoring_side: string | null;
  player_name: string | null;
  action_type: string | null;
  sub_type: string | null;
  description: string | null;
  away_abbreviation?: string | null;
  home_abbreviation?: string | null;
};

function toPoints(
  events: PlayByPlayEvent[],
  teams?: { awayAbbreviation?: string | null; homeAbbreviation?: string | null }
): ChartPoint[] {
  const mapped = events.map((event) => ({
    elapsed_seconds: event.elapsed_seconds,
    score_differential: event.score_differential,
    score_home: event.score_home,
    score_away: event.score_away,
    period: event.period,
    clock: event.clock,
    clock_remaining_seconds: event.clock_remaining_seconds ?? null,
    scoring_side: event.scoring_side ?? null,
    player_name: event.player_name ?? null,
    action_type: event.action_type ?? null,
    sub_type: event.sub_type ?? null,
    description: event.description ?? null,
    away_abbreviation: teams?.awayAbbreviation ?? null,
    home_abbreviation: teams?.homeAbbreviation ?? null,
  }));
  if (mapped.length === 0) return mapped;
  if (mapped[0].elapsed_seconds > 0 || mapped[0].score_differential !== 0) {
    return [
      {
        elapsed_seconds: 0,
        score_differential: 0,
        score_home: 0,
        score_away: 0,
        period: 1,
        clock: "12:00",
        clock_remaining_seconds: 720,
        scoring_side: null,
        player_name: null,
        action_type: null,
        sub_type: null,
        description: "Tip-off",
        away_abbreviation: teams?.awayAbbreviation ?? null,
        home_abbreviation: teams?.homeAbbreviation ?? null,
      },
      ...mapped,
    ];
  }
  return mapped;
}

export function GameFlowChart({
  events,
  flow,
}: {
  events: PlayByPlayEvent[];
  flow?: GameFlow | null;
}) {
  const teams = {
    homeAbbreviation: flow?.home_team_abbreviation,
    awayAbbreviation: flow?.away_team_abbreviation,
  };
  const data = toPoints(events, teams);
  if (data.length === 0) {
    return (
      <EmptyState
        title="No play-by-play data available."
        message="There's no scoring timeline for this game."
      />
    );
  }

  const maxPeriod = Math.max(
    flow?.game_elapsed_seconds && flow.game_elapsed_seconds > 2880 ? 5 : 4,
    ...data.map((point) => point.period ?? 4)
  );
  const ticks = quarterAxisTicks(maxPeriod);
  const biggestRun = selectBiggestRun(events, teams);
  const caption = biggestRun ? formatBiggestRunCaption(biggestRun) : null;
  const runStart = biggestRun?.biggest_run_start_seconds;
  const runEnd = biggestRun?.biggest_run_end_seconds;
  const showRun = caption != null && runStart != null && runEnd != null && runEnd > runStart;
  const plotColors = resolvePlotColors({
    homePrimary: flow?.home_primary_color,
    homeAlternate: flow?.home_alternate_color,
    awayPrimary: flow?.away_primary_color,
    awayAlternate: flow?.away_alternate_color,
  });
  const segments = leadSegments(data, plotColors);
  const runColor =
    biggestRun?.biggest_run_team_abbreviation &&
    biggestRun.biggest_run_team_abbreviation === teams.awayAbbreviation
      ? plotColors.away
      : plotColors.home;

  return (
    <div>
      <div className="h-[420px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#D8D3C6" />
            <XAxis
              type="number"
              dataKey="elapsed_seconds"
              ticks={ticks.map((tick) => tick.seconds)}
              tickFormatter={(value) =>
                ticks.find((tick) => tick.seconds === value)?.label ?? periodLabel(1)
              }
              tick={{ fill: "#5C574F", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              label={{ value: "Quarter", position: "insideBottom", offset: -2, fill: "#5C574F" }}
            />
            <YAxis
              tick={{ fill: "#5C574F", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={44}
              label={{
                value: "Score Differential",
                angle: -90,
                position: "insideLeft",
                fill: "#5C574F",
                style: { textAnchor: "middle" },
              }}
            />
            <ReferenceLine y={0} stroke="#A39C8C" strokeDasharray="4 4" />
            {showRun ? (
              <ReferenceArea
                x1={runStart}
                x2={runEnd}
                fill={runColor}
                fillOpacity={0.18}
                label={{
                  value: caption,
                  position: "insideTop",
                  fill: "#1A1A1A",
                  fontSize: 12,
                }}
              />
            ) : null}
            <Tooltip content={<GameFlowTooltip />} />
            {segments.map((segment, index) => (
              <Line
                key={`${segment.color}-${index}`}
                type="linear"
                data={segment.points}
                dataKey="score_differential"
                stroke={segment.color}
                strokeWidth={2}
                dot={(props: { cx?: number; cy?: number; payload?: ChartPoint }) => {
                  const fill = colorForLeader(
                    leaderFromDifferential(props.payload?.score_differential ?? 0),
                    plotColors
                  );
                  return <circle cx={props.cx} cy={props.cy} r={3} fill={fill} stroke={fill} />;
                }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {caption ? <p className="type-caption mt-2">{caption}</p> : null}
    </div>
  );
}
