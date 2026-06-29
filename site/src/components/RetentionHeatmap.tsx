"use client";

import { useRef } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
  MotionValue,
} from "framer-motion";
import type { RetentionHeatmap as RetentionHeatmapData } from "@/lib/snapshot";

const VISIBLE_COHORTS = 14;

function colorForValue(v: number | null): string {
  if (v === null) return "transparent";
  const t = Math.max(0, Math.min(1, v / 50));
  const r = Math.round(10 + t * (94 - 10));
  const g = Math.round(10 + t * (106 - 10));
  const b = Math.round(15 + t * (210 - 15));
  return `rgb(${r}, ${g}, ${b})`;
}

function StaticCell({ value }: { value: number | null }) {
  if (value === null) {
    return <div className="aspect-square rounded-sm bg-white/[0.02]" />;
  }

  return (
    <div
      style={{ backgroundColor: colorForValue(value) }}
      className="group relative aspect-square rounded-sm"
      title={`${value.toFixed(1)}%`}
    >
      <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-[9px] font-medium text-white/0 transition-colors group-hover:text-white/90">
        {value.toFixed(0)}
      </span>
    </div>
  );
}

function AnimatedCell({
  value,
  index,
  total,
  progress,
}: {
  value: number | null;
  index: number;
  total: number;
  progress: MotionValue<number>;
}) {
  const start = index / total;
  const end = start + 1 / total + 0.15;
  const opacity = useTransform(progress, [start, end], [0, 1]);
  const scale = useTransform(progress, [start, end], [0.6, 1]);

  if (value === null) {
    return <div className="aspect-square rounded-sm bg-white/[0.02]" />;
  }

  return (
    <motion.div
      style={{ opacity, scale, backgroundColor: colorForValue(value) }}
      className="group relative aspect-square rounded-sm"
      title={`${value.toFixed(1)}%`}
    >
      <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-[9px] font-medium text-white/0 transition-colors group-hover:text-white/90">
        {value.toFixed(0)}
      </span>
    </motion.div>
  );
}

export function RetentionHeatmap({ retention }: { retention: RetentionHeatmapData }) {
  const prefersReducedMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.85", "start 0.15"],
  });

  const rows = retention.grid.slice(-VISIBLE_COHORTS);
  const totalCells = rows.length * retention.weeks.length;
  let cellIndex = 0;

  return (
    <div ref={containerRef}>
      <div className="overflow-x-auto rounded-2xl border border-hairline bg-surface p-6">
        <div className="min-w-[640px]">
          <div
            className="grid gap-1"
            style={{
              gridTemplateColumns: `90px repeat(${retention.weeks.length}, 1fr)`,
            }}
          >
            <div />
            {retention.weeks.map((w) => (
              <div
                key={w}
                className="num pb-2 text-center text-[10px] text-faint"
              >
                W{w}
              </div>
            ))}

            {rows.map((row) => {
              const startIdx = cellIndex;
              cellIndex += row.values.length;
              return (
                <div className="contents" key={row.cohort_week}>
                  <div className="num flex items-center justify-end pr-2 text-[11px] text-muted">
                    {row.cohort_week}
                  </div>
                  {row.values.map((v, i) =>
                    prefersReducedMotion ? (
                      <StaticCell key={i} value={v} />
                    ) : (
                      <AnimatedCell
                        key={i}
                        value={v}
                        index={startIdx + i}
                        total={totalCells}
                        progress={scrollYProgress}
                      />
                    )
                  )}
                </div>
              );
            })}
          </div>
        </div>
        <div className="mt-6 flex items-center gap-2 text-xs text-faint">
          <span>0%</span>
          <div className="h-2 w-32 rounded-full bg-gradient-to-r from-[#0a0a0f] to-[#5e6ad2]" />
          <span>50%+</span>
          <span className="ml-4">
            Blank cells = cohort hasn&apos;t reached that week yet (not 0%
            retention)
          </span>
        </div>
      </div>
    </div>
  );
}
