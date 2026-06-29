"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_POINT_COUNT } from "./FieldContext";
import { snapshot } from "@/lib/snapshot";

gsap.registerPlugin(ScrollTrigger);

const { steps, pct_of_signups: pctOfSignups, users_reached: usersReached } =
  snapshot.funnel.overall;

const GATE_COUNT = pctOfSignups.length; // 5: signup, first_view, first_engagement, repeat_engagement, premium_conversion
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

const GATE_Y0 = 150;
const GATE_Y1 = 850;
const FUNNEL_CENTER_X = 500;

// The heatmap grid (Movements 1-2) spans GRID_X0=150 to GRID_X1=850, a
// full width of 700 -- the funnel's mouth should be 50% of that, i.e. a
// half-width of 175, not the same width as the heatmap itself. It tapers
// from there to a tight neck at the real leak (repeat_engagement).
const HALF_WIDTH_BY_GATE = [175, 175, 150, 42, 34];

function gateY(gate: number) {
  return GATE_Y0 + (gate / (GATE_COUNT - 1)) * (GATE_Y1 - GATE_Y0);
}

function halfWidthForGate(gate: number) {
  return HALF_WIDTH_BY_GATE[gate];
}

const survivorsAtGate: number[][] = Array.from({ length: GATE_COUNT }, (_, g) =>
  dropGate.map((d, i) => (d > g ? i : -1)).filter((i) => i !== -1)
);

// Stable per-point randomness, generated once -- used for both fall
// timing (so 168 balls don't move in a synchronized sweep, which reads
// as "traveling in a line" rather than independently falling) and pile
// jitter (so survivors land jumbled, not grid-perfect).
const fallDelay: number[] = Array.from({ length: FIELD_POINT_COUNT }, () => Math.random());
const pileJitter: { dx: number; dy: number; rot: number }[] = Array.from(
  { length: FIELD_POINT_COUNT },
  () => ({
    dx: (Math.random() - 0.5) * 10,
    dy: (Math.random() - 0.5) * 10,
    rot: Math.random(),
  })
);

const MIN_SPACING = 13;

// Lays survivors out as a single wide row when there's room, or packs
// them into a jumbled multi-row pile when the gate is too narrow for
// that many points at a readable spacing -- a few real balls dropped
// through a narrow neck land stacked and offset, not in neat rows, so
// each pile slot gets a stable per-point jitter on top of its grid
// position.
function positionAtGate(pointIndex: number, gate: number) {
  const survivors = survivorsAtGate[gate];
  const rank = survivors.indexOf(pointIndex);
  const n = survivors.length;
  const halfWidth = halfWidthForGate(gate);
  const y = gateY(gate);
  if (n <= 1) return { x: FUNNEL_CENTER_X, y };

  const singleRowSpacing = (2 * halfWidth) / (n - 1);
  if (singleRowSpacing >= MIN_SPACING) {
    const x = FUNNEL_CENTER_X + (rank - (n - 1) / 2) * singleRowSpacing;
    return { x, y };
  }

  const maxPerRow = Math.max(1, Math.floor((2 * halfWidth) / MIN_SPACING) + 1);
  const perRow = Math.min(n, maxPerRow);
  const row = Math.floor(rank / perRow);
  const col = rank % perRow;
  const rowCount = Math.ceil(n / perRow);
  const thisRowCount = Math.min(perRow, n - row * perRow);
  const { dx, dy } = pileJitter[pointIndex];
  const x = FUNNEL_CENTER_X + (col - (thisRowCount - 1) / 2) * MIN_SPACING + dx;
  const clusterY = y + (row - (rowCount - 1) / 2) * MIN_SPACING + dy;
  return { x, y: clusterY };
}

function leanSignAtGate(pointIndex: number, gate: number) {
  const survivors = survivorsAtGate[gate];
  const rank = survivors.indexOf(pointIndex);
  const n = survivors.length;
  if (n <= 1) return Math.random() < 0.5 ? -1 : 1;
  const offset = rank - (n - 1) / 2;
  if (offset === 0) return Math.random() < 0.5 ? -1 : 1;
  return Math.sign(offset);
}

const SURVIVE_COLOR = "#5e6ad2";
const PEEL_COLOR = "#e5484d";

function funnelWallsPath() {
  const left = Array.from({ length: GATE_COUNT }, (_, g) => {
    const hw = halfWidthForGate(g);
    return `${g === 0 ? "M" : "L"} ${FUNNEL_CENTER_X - hw} ${gateY(g)}`;
  }).join(" ");
  const right = Array.from({ length: GATE_COUNT }, (_, g) => {
    const hw = halfWidthForGate(g);
    return `${g === 0 ? "M" : "L"} ${FUNNEL_CENTER_X + hw} ${gateY(g)}`;
  }).join(" ");
  return `${left} ${right}`;
}

// Falls a point from its current position to a target as TWO separate
// tweens: horizontal drift settles in smoothly (ease power1.out), while
// the vertical motion accelerates like an actual fall under gravity
// (ease power2.in) -- a single tween with one ease on both axes is what
// produced the "sliding/traveling" look rather than falling. `delayFrac`
// (0-1, drawn from the stable per-point fallDelay table) staggers each
// ball's start within the phase's own time window, so 168 points don't
// move in a synchronized sweep.
function fallTo(
  tl: gsap.core.Timeline,
  target: SVGCircleElement,
  x: number,
  y: number,
  phaseStart: number,
  phaseSpan: number,
  fallFrac: number,
  fallDuration: number,
  extra?: gsap.TweenVars
) {
  const start = phaseStart + fallFrac * phaseSpan * 0.5;
  tl.to(target, { cx: x, duration: fallDuration, ease: "power1.out", ...extra }, start);
  tl.to(target, { cy: y, duration: fallDuration, ease: "power2.in" }, start);
}

export function Movement3Funnel() {
  const { pointRefs, pulsePathRef } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const hookTextRef = useRef<HTMLParagraphElement>(null);
  const leakTextRef = useRef<HTMLParagraphElement>(null);
  const endTextRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const path = pulsePathRef.current;
    const hookText = hookTextRef.current;
    const leakText = leakTextRef.current;
    const endText = endTextRef.current;
    if (!section || !path || !hookText || !leakText || !endText) return;

    const ctx = gsap.context(() => {
      gsap.set(hookText, { opacity: 0 });
      gsap.set(leakText, { opacity: 0 });
      gsap.set(endText, { opacity: 0 });

      let beat: "none" | "hook" | "leak" | "end" = "none";
      let wallsReady = false;

      function setupWalls() {
        if (wallsReady || !path) return;
        wallsReady = true;
        gsap.set(path, { attr: { d: funnelWallsPath() } });
        const wallLength = path.getTotalLength();
        gsap.set(path, {
          strokeDasharray: wallLength,
          strokeDashoffset: wallLength,
          opacity: 0,
          stroke: "#ededef",
        });
      }

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: `+=${window.innerHeight * 2.6}`,
          scrub: true,
          pin: true,
          onEnter: setupWalls,
          onEnterBack: setupWalls,
          onUpdate: (self) => {
            const p = self.progress;
            if (p > 0.05 && p < 0.3 && beat !== "hook") {
              beat = "hook";
              gsap.to(hookText, { opacity: 1, duration: 0.7, ease: "power1.out" });
              gsap.to(leakText, { opacity: 0, duration: 0.5, ease: "power1.out" });
              gsap.to(endText, { opacity: 0, duration: 0.5, ease: "power1.out" });
            } else if (p >= 0.3 && p < 0.78 && beat !== "leak") {
              beat = "leak";
              gsap.to(hookText, { opacity: 0, duration: 0.5, ease: "power1.out" });
              gsap.to(leakText, {
                opacity: 1,
                duration: 0.7,
                delay: 0.2,
                ease: "power1.out",
              });
              gsap.to(endText, { opacity: 0, duration: 0.5, ease: "power1.out" });
            } else if (p >= 0.78 && beat !== "end") {
              beat = "end";
              gsap.to(leakText, { opacity: 0, duration: 0.5, ease: "power1.out" });
              gsap.to(endText, {
                opacity: 1,
                duration: 0.7,
                delay: 0.2,
                ease: "power1.out",
              });
            } else if (p <= 0.05 && beat !== "none") {
              beat = "none";
              gsap.to(hookText, { opacity: 0, duration: 0.5 });
              gsap.to(leakText, { opacity: 0, duration: 0.5 });
              gsap.to(endText, { opacity: 0, duration: 0.5 });
            }
          },
        },
      });

      tl.to(path, { strokeDashoffset: 0, opacity: 0.35, duration: 0.12, ease: "none" }, 0);
      tl.to(path, { opacity: 0, duration: 0.06 }, 0.92);

      // Phase 0 (0 - ~0.2): every point falls from the heatmap grid into
      // the funnel's mouth row. Real gravity fall (accelerating
      // vertical, gentler horizontal), staggered per-point so it reads
      // as 168 independent drops, not one synchronized block sliding.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        const target = positionAtGate(i, 1);
        gsap.set(ref.current, { fill: SURVIVE_COLOR, opacity: 0.85, r: 7 });
        fallTo(tl, ref.current, target.x, target.y, 0, 0.2, fallDelay[i], 0.35);
      });

      // Phase 1 (0.16 - 0.34): first_engagement gate -- a small, real
      // leak (~7%). Peeled balls fall toward the side they were already
      // leaning, glance off the new narrower wall, and tumble away.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        if (dropGate[i] === 2) {
          const lean = leanSignAtGate(i, 1);
          const wallHalf = halfWidthForGate(2);
          const tx = FUNNEL_CENTER_X + lean * (wallHalf + 50 + Math.random() * 60);
          const ty = gateY(1) + (gateY(2) - gateY(1)) * (0.5 + Math.random() * 0.6);
          fallTo(tl, ref.current, tx, ty, 0.16, 0.18, fallDelay[i], 0.34, {
            fill: PEEL_COLOR,
            opacity: 0,
            rotation: (pileJitter[i].rot - 0.5) * 90,
          });
        } else {
          const target = positionAtGate(i, 2);
          fallTo(tl, ref.current, target.x, target.y, 0.16, 0.18, fallDelay[i], 0.32);
        }
      });

      // Phase 2 (0.36 - 0.76): repeat_engagement -- the real leak and
      // the funnel's steepest pinch. Most of the field can't fit through
      // and tumbles off the wall here; survivors fall on through the
      // neck.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        if (dropGate[i] === 3) {
          const lean = leanSignAtGate(i, 2);
          const wallHalf = halfWidthForGate(3);
          const tx = FUNNEL_CENTER_X + lean * (wallHalf + 70 + Math.random() * 90);
          const ty = gateY(2) + (gateY(3) - gateY(2)) * (0.35 + Math.random() * 0.55);
          fallTo(tl, ref.current, tx, ty, 0.36, 0.4, fallDelay[i], 0.46, {
            fill: PEEL_COLOR,
            opacity: 0,
            rotation: (pileJitter[i].rot - 0.5) * 140,
          });
        } else if (dropGate[i] > 3) {
          const target = positionAtGate(i, 3);
          fallTo(tl, ref.current, target.x, target.y, 0.36, 0.4, fallDelay[i], 0.46, {
            r: 8,
          });
        }
      });

      // Phase 3 (0.78 - 0.92): premium_conversion -- the last, much
      // smaller thinning. Survivors land in the pile with a slight
      // bounce, like balls finally settling at the bottom of the neck.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        if (dropGate[i] === 4) {
          const lean = leanSignAtGate(i, 3);
          const wallHalf = halfWidthForGate(4);
          const tx = FUNNEL_CENTER_X + lean * (wallHalf + 45 + Math.random() * 55);
          const ty = gateY(3) + (gateY(4) - gateY(3)) * (0.5 + Math.random() * 0.5);
          fallTo(tl, ref.current, tx, ty, 0.78, 0.14, fallDelay[i], 0.3, {
            fill: PEEL_COLOR,
            opacity: 0,
            rotation: (pileJitter[i].rot - 0.5) * 100,
          });
        } else if (dropGate[i] === GATE_COUNT) {
          const target = positionAtGate(i, 4);
          const start = 0.78 + fallDelay[i] * 0.07;
          tl.to(
            ref.current,
            { cx: target.x, duration: 0.26, ease: "power1.out" },
            start
          );
          tl.to(
            ref.current,
            {
              cy: target.y,
              opacity: 1,
              r: 9,
              duration: 0.3,
              ease: "bounce.out",
            },
            start
          );
        }
      });

      // Phase 4 (0.92 - 1.0): regroup -- the survivor pile splits into
      // two clusters, setting up Movement 4's two experiment beats.
      const finalSurvivors = survivorsAtGate[GATE_COUNT - 1];
      finalSurvivors.forEach((pointIndex, rank) => {
        const ref = pointRefs[pointIndex];
        if (!ref.current) return;
        const cluster = rank % 2;
        const rankInCluster = Math.floor(rank / 2);
        const clusterX = cluster === 0 ? 350 : 650;
        const { dx, dy } = pileJitter[pointIndex];
        const x = clusterX + (rankInCluster % 4) * 24 - 36 + dx * 0.5;
        const y = 850 + Math.floor(rankInCluster / 4) * 24 + dy * 0.5;
        tl.to(
          ref.current,
          { cx: x, cy: y, duration: 0.4, ease: "power3.inOut" },
          0.92 + (rank / finalSurvivors.length) * 0.06
        );
      });
    }, section);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 h-screen px-6 text-center">
        <p
          ref={hookTextRef}
          className="absolute inset-0 flex items-center justify-center px-8 font-display text-2xl font-medium text-foreground sm:text-4xl"
        >
          {usersReached[0].toLocaleString("en-US")} fans sign up. Almost all of them
          look.
        </p>
        <p
          ref={leakTextRef}
          className="absolute inset-0 flex items-center justify-center px-8 font-display text-2xl font-medium text-[#e5484d] sm:text-4xl"
        >
          Then most of them never come back.
        </p>
        <div
          ref={endTextRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            {usersReached[usersReached.length - 1].toLocaleString("en-US")} stick
            around.
          </p>
          <p className="max-w-md text-lg text-muted">
            That&apos;s the real audience -- {steps[steps.length - 1].replace("_", " ")}.
          </p>
        </div>
      </div>
    </div>
  );
}
