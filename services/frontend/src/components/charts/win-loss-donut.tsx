"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { EmptyState } from "@/components/query-state";
import { formatWinPct } from "@/lib/format";

const COLORS = {
  wins: "#2D5A27",
  losses: "#9B2C22",
};

const tooltipStyle = {
  background: "#FBFAF5",
  border: "1px solid #D8D3C6",
  borderRadius: 0,
  color: "#1A1A1A",
};

export function WinLossDonut({ wins, losses }: { wins: number; losses: number }) {
  const total = wins + losses;
  if (total === 0) {
    return (
      <EmptyState
        title="No record yet"
        message="Win/loss totals will show once games are available."
      />
    );
  }

  const data = [
    { name: "Wins", value: wins },
    { name: "Losses", value: losses },
  ];

  return (
    <div className="relative h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={62}
            outerRadius={88}
            paddingAngle={3}
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.name === "Wins" ? COLORS.wins : COLORS.losses} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-2xl font-semibold">{formatWinPct(wins / total)}</p>
        <p className="text-xs text-muted-foreground">
          {wins}–{losses}
        </p>
      </div>
    </div>
  );
}
