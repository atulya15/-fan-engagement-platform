"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_POINT_COUNT } from "./FieldContext";
import { snapshot } from "@/lib/snapshot";

gsap.registerPlugin(ScrollTrigger);

// Same 14-point cohort Movement 5 left condensed near center.
const { pct_of_signups: pctOfSignups } = snapshot.funnel.overall;
const GATE_COUNT = pctOfSignups.length;
const survivorCounts = pctOfSignups.map((pct) =>
  Math.round((pct / 100) * FIELD_POINT_COUNT)
);
const dropGate: number[] = new Array(FIELD_POINT_COUNT).fill(GATE_COUNT);
for (let g = GATE_COUNT - 1; g >= 1; g--) {
  const dropCount = survivorCounts[g - 1] - survivorCounts[g];
  let assigned = 0;
  for (let i = FIELD_POINT_COUNT - 1; i >= 0 && assigned < dropCount; i--) {
    if (dropGate[i] === GATE_COUNT && i < survivorCounts[g - 1]) {
      dropGate[i] = g;
      assigned++;
    }
  }
}
const finalSurvivors = dropGate
  .map((d, i) => (d === GATE_COUNT ? i : -1))
  .filter((i) => i !== -1);
const cohort = finalSurvivors.filter((_, rank) => rank % 2 === 1);

const { hero, experiments, recommendation_eval } = snapshot;
const feedLift = experiments.feed.primary;
const shippedCount = [experiments.feed, experiments.onboarding, experiments.push].filter(
  (e) => e.decision.recommendation === "ship"
).length;
const coldRecall = recommendation_eval.summary.find(
  (r) => r.method === "content" && r.segment === "cold_only"
);

const CENTER_X = 500;
const CENTER_Y = 500;

// Movement 1's exact zigzag, reused verbatim -- the whole point of this
// beat is that the pulse line comes back as the SAME shape it started
// as, not a new one, paying off "no hard cuts" one more time before
// Movement 7 turns it into the literal dashboard header.
const PULSE_LINE_D =
  "M 80 500 L 280 500 L 320 380 L 400 660 L 460 320 L 500 500 L 920 500";

export function Movement6Scale() {
  const { pointRefs, pulsePathRef } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const kpiRefs = [useRef<HTMLDivElement>(null), useRef<HTMLDivElement>(null), useRef<HTMLDivElement>(null), useRef<HTMLDivElement>(null)];

  useEffect(() => {
    const section = sectionRef.current;
    const path = pulsePathRef.current;
    const kpis = kpiRefs.map((r) => r.current);
    if (!section || !path || kpis.some((k) => !k)) return;
    const kpiEls = kpis as HTMLDivElement[];

    const ctx = gsap.context(() => {
      gsap.set(kpiEls, { opacity: 0 });

      let activeKpi = -1;
      function showKpi(index: number) {
        if (activeKpi === index) return;
        activeKpi = index;
        kpiEls.forEach((el, i) =>
          gsap.to(el, { opacity: i === index ? 1 : 0, duration: 0.5, delay: i === index ? 0.15 : 0, ease: "power1.out" })
        );
      }

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: `+=${window.innerHeight * 2.4}`,
          scrub: true,
          pin: true,
          onUpdate: (self) => {
            const p = self.progress;
            if (p > 0.08 && p < 0.26) showKpi(0);
            else if (p >= 0.26 && p < 0.42) showKpi(1);
            else if (p >= 0.42 && p < 0.58) showKpi(2);
            else if (p >= 0.58 && p < 0.76) showKpi(3);
            else if (p >= 0.76 || p <= 0.08) {
              if (activeKpi !== -1) {
                activeKpi = -1;
                kpiEls.forEach((el) => gsap.to(el, { opacity: 0, duration: 0.4 }));
              }
            }
          },
        },
      });

      // Phase 0 (0 - 0.06): fast snap -- the loose graph condenses
      // sharply into one tight cluster. Quick, not gradual: this is a
      // hard cut in pacing (not in continuity -- it's still the same
      // points), marking the shift from "here's how it works" into
      // "here's what it added up to."
      cohort.forEach((pointIndex, idx) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        const angle = (idx / cohort.length) * Math.PI * 2;
        tl.to(
          ref,
          {
            cx: CENTER_X + Math.cos(angle) * 14,
            cy: CENTER_Y + Math.sin(angle) * 14,
            r: 5,
            opacity: 0.7,
            duration: 0.06,
            ease: "power3.in",
          },
          0
        );
      });
      tl.to(path, { opacity: 0, duration: 0.04 }, 0);

      // Phase 1 (0.08 - 0.76): the KPI sequence. Each number gets its
      // own held beat (via showKpi above, time-based not scroll-distance
      // based -- see Movement1Hook.tsx for why that matters), while the
      // condensed cluster sits quietly behind it, gently breathing.
      cohort.forEach((pointIndex, idx) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        tl.to(
          ref,
          { opacity: 0.35, duration: 0.5, ease: "sine.inOut" },
          0.1 + (idx % 3) * 0.15
        );
        tl.to(
          ref,
          { opacity: 0.7, duration: 0.5, ease: "sine.inOut" },
          0.4 + (idx % 3) * 0.15
        );
      });

      // Phase 2 (0.78 - 0.88): collapse -- every point converges to
      // exactly one point and disappears.
      cohort.forEach((pointIndex, idx) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        tl.to(
          ref,
          { cx: CENTER_X, cy: CENTER_Y, opacity: 0, r: 2, duration: 0.3, ease: "power2.in" },
          0.78 + (idx / cohort.length) * 0.06
        );
      });

      // Phase 3 (0.88 - 1.0): unfurl -- the shared path becomes the
      // pulse line again, drawing back out from that single point.
      tl.call(
        () => {
          if (!path) return;
          gsap.set(path, {
            attr: { d: PULSE_LINE_D },
            opacity: 0,
            stroke: "#ededef",
            strokeWidth: 3,
          });
          const len = path.getTotalLength();
          gsap.set(path, { strokeDasharray: len, strokeDashoffset: len });
        },
        undefined,
        0.88
      );
      tl.to(path, { opacity: 1, strokeDashoffset: 0, duration: 0.34, ease: "power2.inOut" }, 0.89);
    }, section);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 flex h-screen flex-col items-center justify-center px-6 text-center">
        <div ref={kpiRefs[0]} className="absolute flex flex-col items-center gap-2">
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            {hero.total_events.toLocaleString("en-US")}
          </p>
          <p className="text-lg text-muted">events, across {hero.simulation_months} months.</p>
        </div>
        <div ref={kpiRefs[1]} className="absolute flex flex-col items-center gap-2">
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            {Math.round(feedLift.relative_lift_pct)}%
          </p>
          <p className="text-lg text-muted">lift in day-7 retention from one shipped experiment.</p>
        </div>
        <div ref={kpiRefs[2]} className="absolute flex flex-col items-center gap-2">
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            {shippedCount} / 3
          </p>
          <p className="text-lg text-muted">experiments shipped -- real, significant, guardrails clean.</p>
        </div>
        <div ref={kpiRefs[3]} className="absolute flex flex-col items-center gap-2">
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            {coldRecall ? coldRecall.recall_at_10.toFixed(2) : "0.20"}
          </p>
          <p className="text-lg text-muted">recall@10, even for fans with zero history.</p>
        </div>
      </div>
    </div>
  );
}
