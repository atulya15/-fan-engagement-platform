"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_POINT_COUNT } from "./FieldContext";
import { snapshot } from "@/lib/snapshot";

gsap.registerPlugin(ScrollTrigger);

// Recomputes exactly which points survived Movement 3's funnel (same
// deterministic algorithm, same data) so Movement 4 picks up the same
// final two-cluster positions Movement 3 left them in -- no
// repositioning, just retargeting color/opacity on the same points.
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
const controlCluster = finalSurvivors.filter((_, rank) => rank % 2 === 0);
const treatmentCluster = finalSurvivors.filter((_, rank) => rank % 2 === 1);

const feed = snapshot.experiments.feed;
const push = snapshot.experiments.push;
const peekLook3 = push.sequential_peeks?.[2];
// The snapshot.ts type declares sequential_alphas as objects with an
// alpha_spent field, but the real JSON (see build_snapshot.py) writes it
// as a plain number[] -- the type doesn't match the actual data here.
const alphaLook3 = push.sequential_alphas?.[2] as unknown as number | undefined;

const CONTROL_COLOR = "#8b8b94";
const TREATMENT_COLOR = "#5e6ad2";
const WRONG_COLOR = "#e5484d";

export function Movement4Experiments() {
  const { pointRefs } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const beatARef = useRef<HTMLDivElement>(null);
  const beatACorrectRef = useRef<HTMLDivElement>(null);
  const beatBRef = useRef<HTMLDivElement>(null);
  const beatBCorrectRef = useRef<HTMLDivElement>(null);
  const shipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const beatA = beatARef.current;
    const beatACorrect = beatACorrectRef.current;
    const beatB = beatBRef.current;
    const beatBCorrect = beatBCorrectRef.current;
    const ship = shipRef.current;
    if (!section || !beatA || !beatACorrect || !beatB || !beatBCorrect || !ship) return;

    const ctx = gsap.context(() => {
      gsap.set([beatA, beatACorrect, beatB, beatBCorrect, ship], { opacity: 0 });

      // Both clusters already sit at Movement 3's final positions --
      // only color/opacity is set here, never cx/cy.
      controlCluster.forEach((i) => {
        const ref = pointRefs[i].current;
        if (ref) gsap.set(ref, { fill: CONTROL_COLOR, opacity: 0.6 });
      });
      treatmentCluster.forEach((i) => {
        const ref = pointRefs[i].current;
        if (ref) gsap.set(ref, { fill: TREATMENT_COLOR, opacity: 0.85 });
      });

      type Beat = "none" | "a" | "aCorrect" | "b" | "bCorrect" | "ship";
      let beat: Beat = "none";
      const allBeats = [beatA, beatACorrect, beatB, beatBCorrect, ship];

      function showBeat(next: Beat, visible: HTMLElement) {
        if (beat === next) return;
        beat = next;
        allBeats.forEach((el) => gsap.to(el, { opacity: 0, duration: 0.4, ease: "power1.out" }));
        gsap.to(visible, { opacity: 1, duration: 0.6, delay: 0.2, ease: "power1.out" });
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
            if (p > 0.04 && p < 0.22) showBeat("a", beatA);
            else if (p >= 0.22 && p < 0.4) showBeat("aCorrect", beatACorrect);
            else if (p >= 0.4 && p < 0.58) showBeat("b", beatB);
            else if (p >= 0.58 && p < 0.82) showBeat("bCorrect", beatBCorrect);
            else if (p >= 0.82) showBeat("ship", ship);
            else if (p <= 0.04 && beat !== "none") {
              beat = "none";
              allBeats.forEach((el) =>
                gsap.to(el, { opacity: 0, duration: 0.4, ease: "power1.out" })
              );
            }
          },
        },
      });

      // Beat A (0.05 - 0.2): the feed guardrail dips -- treatment
      // cluster flashes red, as if something went wrong.
      treatmentCluster.forEach((i, idx) => {
        const ref = pointRefs[i].current;
        if (!ref) return;
        tl.to(
          ref,
          { fill: WRONG_COLOR, duration: 0.3, ease: "power1.inOut" },
          0.05 + (idx / treatmentCluster.length) * 0.05
        );
      });

      // Correction (0.24 - 0.38): it's noise, not a real drop -- the
      // actual primary metric (day-7 retention) nearly doubled.
      treatmentCluster.forEach((i, idx) => {
        const ref = pointRefs[i].current;
        if (!ref) return;
        tl.to(
          ref,
          { fill: TREATMENT_COLOR, opacity: 1, r: 8, duration: 0.3, ease: "power1.inOut" },
          0.24 + (idx / treatmentCluster.length) * 0.05
        );
      });

      // Beat B (0.42 - 0.56): the push peeking problem -- at 75% of the
      // data it already LOOKS significant.
      treatmentCluster.forEach((i, idx) => {
        const ref = pointRefs[i].current;
        if (!ref) return;
        tl.to(
          ref,
          { opacity: 0.45, duration: 0.2, ease: "power1.inOut" },
          0.42 + (idx / treatmentCluster.length) * 0.04
        );
      });

      // Correction (0.62 - 0.78): wait for the full sample -- now it's
      // genuinely, properly significant.
      treatmentCluster.forEach((i, idx) => {
        const ref = pointRefs[i].current;
        if (!ref) return;
        tl.to(
          ref,
          { opacity: 1, r: 9, duration: 0.3, ease: "power1.inOut" },
          0.62 + (idx / treatmentCluster.length) * 0.04
        );
      });

      // Final (0.84 - 1.0): the control cluster -- the loser of both
      // experiments -- falls away entirely. Only the treatment cluster
      // (the winner of both) survives into Movement 5.
      controlCluster.forEach((i, idx) => {
        const ref = pointRefs[i].current;
        if (!ref) return;
        tl.to(
          ref,
          {
            opacity: 0,
            cy: `+=${40 + Math.random() * 60}`,
            cx: `+=${(Math.random() - 0.5) * 80}`,
            duration: 0.4,
            ease: "power2.in",
          },
          0.84 + (idx / controlCluster.length) * 0.1
        );
      });
    }, section);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 h-screen px-6 text-center">
        <div
          ref={beatARef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-[#e5484d] sm:text-4xl">
            The guardrail just dipped.
          </p>
          <p className="max-w-md text-muted">
            {feed.name}: average session length looks like it dropped after
            shipping personalization.
          </p>
        </div>
        <div
          ref={beatACorrectRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-foreground sm:text-4xl">
            It&apos;s noise, not a real drop.
          </p>
          <p className="max-w-md text-muted">
            p = {feed.guardrail.p_value.toFixed(2)} on the guardrail -- not
            significant. Meanwhile day-7 retention nearly doubled.
          </p>
        </div>
        <div
          ref={beatBRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-foreground sm:text-4xl">
            At 75% of the data, this already looks significant.
          </p>
          <p className="max-w-md text-muted">
            {push.name}: p = {peekLook3 ? peekLook3.p_value.toFixed(3) : "--"}{" "}
            at look 3.
          </p>
        </div>
        <div
          ref={beatBCorrectRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-8"
        >
          <p className="font-display text-2xl font-medium text-[#e5484d] sm:text-4xl">
            Stop there, and you&apos;d be wrong more often than 5% of the time.
          </p>
          <p className="max-w-md text-muted">
            The properly-adjusted threshold at that look was{" "}
            {alphaLook3 !== undefined ? alphaLook3.toFixed(3) : "--"}, not
            0.05. Wait for the full sample.
          </p>
        </div>
        <div
          ref={shipRef}
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8"
        >
          <p className="num text-xs uppercase tracking-[0.2em] text-faint">
            Decision
          </p>
          <p className="font-display text-4xl font-semibold text-foreground sm:text-6xl">
            SHIP
          </p>
          <p className="max-w-md text-muted">
            Both experiments: real, significant, guardrails clean.
          </p>
        </div>
      </div>
    </div>
  );
}
