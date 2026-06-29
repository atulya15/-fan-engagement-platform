"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_POINT_COUNT } from "./FieldContext";
import { snapshot } from "@/lib/snapshot";

gsap.registerPlugin(ScrollTrigger);

// Recomputes the same 28 funnel survivors, then the same treatment-only
// half Movement 4 left visible (the control half faded to opacity 0
// there) -- this movement works with exactly those 14 points, picking
// up where Movement 4 actually left them, not a fresh selection.
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
const cohort = finalSurvivors.filter((_, rank) => rank % 2 === 1); // treatment half

// Real cold-start ratio from recommendation_eval (70 cold / 800 test
// users = 8.75%) -- applied to our 14-point cohort, that's 1 cold node,
// not an arbitrary dramatic fraction.
const { n_cold, n_test_users } = snapshot.recommendation_eval;
const coldCount = Math.max(1, Math.round((n_cold / n_test_users) * cohort.length));
const coldNodes = cohort.slice(0, coldCount);
const warmNodes = cohort.slice(coldCount);

const cfCold = snapshot.recommendation_eval.summary.find(
  (r) => r.method === "cf" && r.segment === "cold_only"
);
const contentCold = snapshot.recommendation_eval.summary.find(
  (r) => r.method === "content" && r.segment === "cold_only"
);

const GRAPH_CENTER_X = 500;
const GRAPH_CENTER_Y = 460;
const GRAPH_RADIUS = 170;

// Organic, non-grid layout via the golden angle -- the same trick used
// for phyllotaxis/sunflower-seed patterns, so warm nodes settle into a
// natural-looking cluster rather than a grid or a perfect circle.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
function warmNodePosition(rank: number, total: number) {
  const r = GRAPH_RADIUS * Math.sqrt((rank + 0.5) / total);
  const theta = rank * GOLDEN_ANGLE;
  return {
    x: GRAPH_CENTER_X + r * Math.cos(theta),
    y: GRAPH_CENTER_Y + r * Math.sin(theta),
  };
}

const warmPositions = warmNodes.map((_, rank) => warmNodePosition(rank, warmNodes.length));
const coldPositions = coldNodes.map((_, i) => ({
  x: 190 + i * 60,
  y: 250,
}));

// A handful of plausible "similar fan" edges between warm nodes -- each
// node links to its two nearest neighbors in the layout, which is also
// just enough structure to read as a real network rather than random
// scribbles.
function nearestTwo(i: number) {
  const distances = warmPositions
    .map((p, j) => ({
      j,
      d: Math.hypot(p.x - warmPositions[i].x, p.y - warmPositions[i].y),
    }))
    .filter((d) => d.j !== i)
    .sort((a, b) => a.d - b.d);
  return distances.slice(0, 2).map((d) => d.j);
}

function warmEdgesPath() {
  const segments: string[] = [];
  warmPositions.forEach((p, i) => {
    nearestTwo(i).forEach((j) => {
      const q = warmPositions[j];
      segments.push(`M ${p.x} ${p.y} L ${q.x} ${q.y}`);
    });
  });
  return segments.join(" ");
}

// The cold node's nearest warm neighbor -- this is the literal
// "threading in" edge content-based similarity draws once collaborative
// filtering has nothing to go on.
function coldThreadEdgesPath() {
  const segments: string[] = [warmEdgesPath()];
  coldPositions.forEach((c) => {
    let nearest = 0;
    let best = Infinity;
    warmPositions.forEach((p, j) => {
      const d = Math.hypot(p.x - c.x, p.y - c.y);
      if (d < best) {
        best = d;
        nearest = j;
      }
    });
    const p = warmPositions[nearest];
    segments.push(`M ${c.x} ${c.y} L ${p.x} ${p.y}`);
  });
  return segments.join(" ");
}

const WARM_COLOR = "#5e6ad2";
const COLD_COLOR = "#8b8b94";
const FAIL_COLOR = "#e5484d";

export function Movement5Recommendations() {
  const { pointRefs, pulsePathRef } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const beatGraphRef = useRef<HTMLDivElement>(null);
  const beatColdRef = useRef<HTMLDivElement>(null);
  const beatThreadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const path = pulsePathRef.current;
    const beatGraph = beatGraphRef.current;
    const beatCold = beatColdRef.current;
    const beatThread = beatThreadRef.current;
    if (!section || !path || !beatGraph || !beatCold || !beatThread) return;

    const ctx = gsap.context(() => {
      gsap.set([beatGraph, beatCold, beatThread], { opacity: 0 });

      type Beat = "none" | "graph" | "cold" | "thread";
      let beat: Beat = "none";
      const allBeats = [beatGraph, beatCold, beatThread];
      function showBeat(next: Beat, visible: HTMLElement) {
        if (beat === next) return;
        beat = next;
        allBeats.forEach((el) => gsap.to(el, { opacity: 0, duration: 0.4, ease: "power1.out" }));
        gsap.to(visible, { opacity: 1, duration: 0.6, delay: 0.2, ease: "power1.out" });
      }

      let edgesReady = false;
      function setupEdges() {
        if (edgesReady || !path) return;
        edgesReady = true;
        gsap.set(path, { attr: { d: warmEdgesPath() } });
        const len = path.getTotalLength();
        gsap.set(path, {
          strokeDasharray: len,
          strokeDashoffset: len,
          opacity: 0,
          stroke: WARM_COLOR,
          strokeWidth: 1.5,
        });
      }

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: `+=${window.innerHeight * 2.2}`,
          scrub: true,
          pin: true,
          onEnter: setupEdges,
          onEnterBack: setupEdges,
          onUpdate: (self) => {
            const p = self.progress;
            if (p > 0.06 && p < 0.32) showBeat("graph", beatGraph);
            else if (p >= 0.32 && p < 0.55) showBeat("cold", beatCold);
            else if (p >= 0.55) showBeat("thread", beatThread);
            else if (p <= 0.06 && beat !== "none") {
              beat = "none";
              allBeats.forEach((el) =>
                gsap.to(el, { opacity: 0, duration: 0.4, ease: "power1.out" })
              );
            }
          },
        },
      });

      // Phase 0 (0 - 0.15): the surviving cohort settles from Movement
      // 4's cluster into the graph layout. Warm nodes spread into the
      // organic cluster; the cold node(s) land isolated, off to the
      // side -- no edges reach them yet.
      warmNodes.forEach((pointIndex, rank) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        const target = warmPositions[rank];
        tl.to(
          ref,
          { cx: target.x, cy: target.y, fill: WARM_COLOR, r: 8, duration: 0.4, ease: "power2.inOut" },
          0
        );
      });
      coldNodes.forEach((pointIndex, i) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        const target = coldPositions[i];
        tl.to(
          ref,
          { cx: target.x, cy: target.y, fill: COLD_COLOR, opacity: 0.6, r: 8, duration: 0.4, ease: "power2.inOut" },
          0
        );
      });

      // Draw the warm graph's edges in.
      tl.to(path, { strokeDashoffset: 0, opacity: 0.3, duration: 0.16, ease: "none" }, 0.1);

      // Phase 1 (0.34 - 0.5): collaborative filtering has nothing to go
      // on for a brand-new fan -- the cold node pulses red, isolated.
      coldNodes.forEach((pointIndex) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        tl.to(ref, { fill: FAIL_COLOR, r: 10, duration: 0.25, ease: "power1.inOut" }, 0.34);
        tl.to(ref, { r: 8, duration: 0.25, ease: "power1.inOut" }, 0.5);
      });

      // Phase 2 (0.56 - 0.7): content-based similarity threads the cold
      // node into the graph -- new edges appear, node brightens to match
      // the warm color.
      tl.call(
        () => {
          if (!path) return;
          gsap.set(path, { attr: { d: coldThreadEdgesPath() } });
          const len = path.getTotalLength();
          gsap.set(path, { strokeDasharray: len, strokeDashoffset: 0 });
        },
        undefined,
        0.56
      );
      tl.fromTo(
        path,
        { opacity: 0.15 },
        { opacity: 0.35, duration: 0.3, ease: "power1.inOut" },
        0.56
      );
      coldNodes.forEach((pointIndex) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        tl.to(
          ref,
          { fill: WARM_COLOR, opacity: 1, duration: 0.35, ease: "power1.inOut" },
          0.6
        );
      });

      // Phase 3 (0.85 - 1.0): pull back -- the whole graph condenses
      // toward a tighter cluster around center, handing off into
      // Movement 6's blueprint. Absolute targets pulled halfway toward
      // GRAPH_CENTER_X/Y from each node's current graph position (a
      // smaller copy of the same layout, not a fly-off).
      const allNodes = [...warmNodes, ...coldNodes];
      const allPositions = [...warmPositions, ...coldPositions];
      allNodes.forEach((pointIndex, idx) => {
        const ref = pointRefs[pointIndex].current;
        if (!ref) return;
        const current = allPositions[idx];
        const x = GRAPH_CENTER_X + (current.x - GRAPH_CENTER_X) * 0.4;
        const y = GRAPH_CENTER_Y + (current.y - GRAPH_CENTER_Y) * 0.4;
        tl.to(
          ref,
          { cx: x, cy: y, duration: 0.3, ease: "power2.inOut" },
          0.85 + (idx / allNodes.length) * 0.05
        );
      });
      tl.to(path, { opacity: 0.1, duration: 0.2 }, 0.85);
    }, section);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 h-screen px-6 text-center">
        <div
          ref={beatGraphRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-foreground sm:text-4xl">
            Similar fans, connected.
          </p>
          <p className="max-w-md text-muted">
            Every survivor of the funnel, linked to who they&apos;re most
            alike.
          </p>
        </div>
        <div
          ref={beatColdRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-[#e5484d] sm:text-4xl">
            A brand-new fan has no history yet.
          </p>
          <p className="max-w-md text-muted">
            Collaborative filtering needs past behavior to work -- recall@10
            ={" "}
            {cfCold ? cfCold.recall_at_10.toFixed(2) : "0"} for cold-start
            users.
          </p>
        </div>
        <div
          ref={beatThreadRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-foreground sm:text-4xl">
            Content-based similarity still finds them something.
          </p>
          <p className="max-w-md text-muted">
            recall@10 climbs to{" "}
            {contentCold ? contentCold.recall_at_10.toFixed(2) : "--"} just
            from what they&apos;ve looked at, no history of others required.
          </p>
        </div>
      </div>
    </div>
  );
}
