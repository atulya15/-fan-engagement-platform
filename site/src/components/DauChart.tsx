"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import type { DauSeries } from "@/lib/snapshot";

export function DauChart({ series }: { series: DauSeries }) {
  const data = series.dates.map((date, i) => ({
    date,
    dau: series.dau[i],
    wau: series.wau[i],
    mau: series.mau[i],
  }));

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -16 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.06)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            stroke="var(--color-foreground-faint)"
            fontSize={10}
            tickFormatter={(v: string) => v.slice(5)}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis stroke="var(--color-foreground-faint)" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: "#0a0a0c",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="mau" stroke="#3fb950" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="wau" stroke="#818cf8" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="dau" stroke="#5e6ad2" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
