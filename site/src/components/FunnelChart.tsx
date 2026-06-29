"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import type { FunnelOverall } from "@/lib/snapshot";

const STEP_LABELS: Record<string, string> = {
  signup: "Signup",
  first_view: "First view",
  first_engagement: "First engagement",
  repeat_engagement: "Repeat engagement",
  premium_conversion: "Premium conversion",
};

export function FunnelChartView({ funnel }: { funnel: FunnelOverall }) {
  const data = funnel.steps.map((step, i) => ({
    step: STEP_LABELS[step] ?? step,
    pct: funnel.pct_of_signups[i],
    users: funnel.users_reached[i],
    stepOverStep: funnel.pct_of_previous_step[i],
  }));

  // The leak point: the step with the lowest step-over-step conversion.
  const leakIndex = data
    .map((d, i) => ({ i, v: d.stepOverStep }))
    .filter((d) => d.v !== null)
    .reduce((min, d) => (d.v! < min.v! ? d : min), { i: -1, v: 101 }).i;

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            stroke="var(--color-foreground-faint)"
            fontSize={11}
          />
          <YAxis
            type="category"
            dataKey="step"
            width={140}
            stroke="var(--color-foreground-muted)"
            fontSize={12}
          />
          <Tooltip
            contentStyle={{
              background: "#0a0a0c",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value, _name, item) => {
              const v = Number(value);
              const users = (item?.payload as { users: number })?.users ?? 0;
              return [`${users.toLocaleString("en-US")} users (${v.toFixed(1)}% of signups)`, "Reached"];
            }}
          />
          <Bar dataKey="pct" radius={[0, 6, 6, 0]} barSize={28}>
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={i === leakIndex ? "#f47174" : "#5e6ad2"}
              />
            ))}
            <LabelList
              dataKey="pct"
              position="right"
              formatter={(v) => `${Number(v).toFixed(0)}%`}
              fill="var(--color-foreground)"
              fontSize={12}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
