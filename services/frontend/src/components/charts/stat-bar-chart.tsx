"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/query-state";

export type StatBarSeries = {
  dataKey: string;
  fill: string;
  name?: string;
};

const tooltipStyle = {
  background: "#FBFAF5",
  border: "1px solid #D8D3C6",
  borderRadius: 0,
  color: "#1A1A1A",
};

export function StatBarChart({
  data,
  xKey = "name",
  bars,
}: {
  data: Record<string, string | number>[];
  xKey?: string;
  bars: StatBarSeries[];
}) {
  if (data.length === 0) {
    return <EmptyState title="No chart data" message="Nothing to chart yet." />;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#D8D3C6" vertical={false} />
          <XAxis
            dataKey={xKey}
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
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          {bars.map((bar) => (
            <Bar
              key={bar.dataKey}
              dataKey={bar.dataKey}
              name={bar.name ?? bar.dataKey}
              fill={bar.fill}
              radius={[0, 0, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
