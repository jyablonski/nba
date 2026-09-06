"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/query-state";

export type SeasonPoint = {
  season: string;
  ppg: number;
};

const tooltipStyle = {
  background: "#FBFAF5",
  border: "1px solid #D8D3C6",
  borderRadius: 0,
  color: "#1A1A1A",
};

export function SeasonLineChart({ data }: { data: SeasonPoint[] }) {
  if (data.length === 0) {
    return <EmptyState title="No season averages" message="No PPG by season to show yet." />;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#D8D3C6" vertical={false} />
          <XAxis
            dataKey="season"
            tick={{ fill: "#5C574F", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: "#5C574F", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => [`${Number(value).toFixed(1)}`, "PPG"]}
          />
          <Line
            type="monotone"
            dataKey="ppg"
            stroke="#2D5A27"
            strokeWidth={2}
            dot={{ r: 3, fill: "#2D5A27" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
