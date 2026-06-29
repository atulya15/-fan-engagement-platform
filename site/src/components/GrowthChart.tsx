"use client";

import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import type { Growth } from "@/lib/snapshot";

export function GrowthChartView({ growth }: { growth: Growth }) {
  const data = growth.weeks.map((week, i) => ({
    week,
    new_users: growth.new_users[i],
    returning_users: growth.returning_users[i],
    resurrected_users: growth.resurrected_users[i],
    churned_users: growth.churned_users[i],
    quick_ratio: growth.quick_ratio[i],
  }));

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -16 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.06)"
            vertical={false}
          />
          <XAxis
            dataKey="week"
            stroke="var(--color-foreground-faint)"
            fontSize={10}
            tickFormatter={(v: string) => v.slice(5)}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis
            yAxisId="left"
            stroke="var(--color-foreground-faint)"
            fontSize={11}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="var(--color-foreground-faint)"
            fontSize={11}
            domain={[0, 2]}
          />
          <Tooltip
            contentStyle={{
              background: "#0a0a0c",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar
            yAxisId="left"
            dataKey="new_users"
            stackId="a"
            fill="#5e6ad2"
            radius={[2, 2, 0, 0]}
          />
          <Bar
            yAxisId="left"
            dataKey="returning_users"
            stackId="a"
            fill="rgba(94,106,210,0.35)"
            radius={[2, 2, 0, 0]}
          />
          <Bar
            yAxisId="left"
            dataKey="resurrected_users"
            stackId="a"
            fill="#3fb950"
            radius={[2, 2, 0, 0]}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="churned_users"
            stroke="#f47174"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={false}
          />
          <ReferenceLine
            yAxisId="right"
            y={1}
            stroke="#d29922"
            strokeDasharray="4 4"
            label={{
              value: "breakeven",
              position: "insideTopRight",
              fill: "#d29922",
              fontSize: 10,
            }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="quick_ratio"
            stroke="#f4b942"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
