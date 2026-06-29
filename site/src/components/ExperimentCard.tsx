"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { Experiment } from "@/lib/snapshot";
import { Card } from "./Section";

export function ExperimentCardView({ experiment }: { experiment: Experiment }) {
  const { primary, decision, guardrail, guardrail_metric } = experiment;
  const liftPositive = primary.relative_lift_pct >= 0;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <p className="text-xs font-medium uppercase tracking-wide text-faint">
          {experiment.name}
        </p>
        <p className="mt-1 text-sm text-muted">{experiment.primary_metric}</p>

        <div className="mt-6 flex items-baseline gap-3">
          <span
            className={`text-4xl font-semibold ${
              liftPositive ? "text-[#3fb950]" : "text-[#f47174]"
            }`}
          >
            {liftPositive ? "+" : ""}
            {primary.relative_lift_pct.toFixed(1)}%
          </span>
          <span className="text-sm text-muted">relative lift</span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-faint">p-value</p>
            <p className="num text-foreground">
              {primary.p_value < 0.001 ? "<0.001" : primary.p_value.toFixed(3)}
            </p>
          </div>
          <div>
            <p className="text-faint">95% CI</p>
            <p className="num text-foreground">
              [{primary.ci_low.toFixed(2)}, {primary.ci_high.toFixed(2)}]
            </p>
          </div>
          <div>
            <p className="text-faint">Guardrail ({guardrail_metric})</p>
            <p
              className={`num ${
                experiment.guardrail_ok ? "text-[#3fb950]" : "text-[#f47174]"
              }`}
            >
              {guardrail.diff >= 0 ? "+" : ""}
              {guardrail.diff.toFixed(2)} ({experiment.guardrail_ok ? "OK" : "violated"})
            </p>
          </div>
          <div>
            <p className="text-faint">Sample size</p>
            <p className="num text-foreground">
              {primary.n_a.toLocaleString("en-US")} / {primary.n_b.toLocaleString("en-US")}
            </p>
          </div>
          {experiment.cuped_variance_reduction_pct !== undefined && (
            <div>
              <p className="text-faint">CUPED variance reduction</p>
              <p className="num text-foreground">
                {experiment.cuped_variance_reduction_pct.toFixed(1)}%
              </p>
            </div>
          )}
          <div>
            <p className="text-faint">Required n / arm</p>
            <p className="num text-foreground">
              {Math.round(experiment.required_n_per_arm).toLocaleString("en-US")}
            </p>
          </div>
        </div>

        <div className="mt-6 rounded-lg border border-hairline bg-elevated/40 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-accent">
            Ship decision: {decision.recommendation}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            {decision.reason}
          </p>
        </div>
      </Card>

      {experiment.segment_results.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-foreground">
            Effect by acquisition channel
          </p>
          <p className="mt-1 text-sm text-muted">
            Lift broken down by segment — checks whether the effect is
            uniform or concentrated in one channel.
          </p>
          <div className="mt-4 space-y-3">
            {experiment.segment_results.map((s) => (
              <div
                key={s.segment}
                className="flex items-center justify-between rounded-lg border border-hairline bg-elevated/30 px-4 py-2.5 text-sm"
              >
                <span className="capitalize text-muted">
                  {s.segment.replace(/_/g, " ")}
                </span>
                <span
                  className={`num ${
                    s.result.relative_lift_pct >= 0
                      ? "text-[#3fb950]"
                      : "text-[#f47174]"
                  }`}
                >
                  {s.result.relative_lift_pct >= 0 ? "+" : ""}
                  {s.result.relative_lift_pct.toFixed(1)}%
                  <span className="ml-2 text-faint">
                    p={s.result.p_value.toFixed(3)}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <SequentialPeekCard experiment={experiment} />
      )}
    </div>
  );
}

export function SequentialPeekCard({ experiment }: { experiment: Experiment }) {
  if (!experiment.sequential_peeks) return null;
  const peekData = experiment.sequential_peeks.map((p) => ({
    look: p.look,
    p_value: p.p_value,
  }));
  const firstSig = peekData.findIndex((p) => p.p_value < 0.05) + 1;

  return (
    <Card>
      <p className="text-sm font-medium text-foreground">
        The peeking problem
      </p>
      <p className="mt-1 text-sm text-muted">
        p-value at each sequential look — naive peeking would have called
        this significant at look {firstSig || "—"} of {peekData.length},
        before the pre-registered sample size was reached.
      </p>
      <div className="mt-4 h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={peekData}>
            <XAxis
              dataKey="look"
              stroke="var(--color-foreground-faint)"
              fontSize={10}
            />
            <YAxis
              stroke="var(--color-foreground-faint)"
              fontSize={10}
              domain={[0, 1]}
            />
            <Tooltip
              contentStyle={{
                background: "#0a0a0c",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <ReferenceLine
              y={0.05}
              stroke="#f47174"
              strokeDasharray="4 4"
              label={{
                value: "α = 0.05",
                position: "insideTopRight",
                fill: "#f47174",
                fontSize: 10,
              }}
            />
            <Line
              type="monotone"
              dataKey="p_value"
              stroke="#818cf8"
              strokeWidth={2}
              dot={{ r: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
