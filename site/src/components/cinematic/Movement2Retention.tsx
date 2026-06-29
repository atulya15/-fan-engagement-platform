"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_COLUMNS, FIELD_ROWS } from "./FieldContext";
import { snapshot } from "@/lib/snapshot";

gsap.registerPlugin(ScrollTrigger);

// Real retention data, flattened in the same row-major order Movement 1's
// gridPosition() already lays the 168 points out in (index % FIELD_COLUMNS
// = week column, floor(index / FIELD_COLUMNS) = cohort row) -- so this
// movement never repositions a single point. It only retargets the same
// grid Movement 1 left behind into real fill colors.
const visibleCohorts = snapshot.retention.heatmap.grid.slice(-FIELD_ROWS);
const cellValues: (number | null)[] = [];
visibleCohorts.forEach((row) => {
  for (let c = 0; c < FIELD_COLUMNS; c++) {
    cellValues.push(row.values[c] ?? null);
  }
});

function colorForValue(v: number | null): string {
  if (v === null) return "#1a1a1f";
  const t = Math.max(0, Math.min(1, v / 50));
  const r = Math.round(10 + t * (94 - 10));
  const g = Math.round(10 + t * (106 - 10));
  const b = Math.round(15 + t * (210 - 15));
  return `rgb(${r}, ${g}, ${b})`;
}

export function Movement2Retention() {
  const { pointRefs } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const wrongTextRef = useRef<HTMLParagraphElement>(null);
  const rightTextRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const wrongText = wrongTextRef.current;
    const rightText = rightTextRef.current;
    if (!section || !wrongText || !rightText) return;

    const ctx = gsap.context(() => {
      gsap.set(wrongText, { opacity: 0 });
      gsap.set(rightText, { opacity: 0 });

      // Headline beats are independent, fixed-duration tweens triggered
      // by scroll-position thresholds -- not part of the scrubbed
      // timeline itself. See Movement1Hook.tsx for why: a scrubbed tween
      // has no time dimension of its own, so a fast scroll always
      // resolves it in well under a second regardless of scroll distance.
      let beat: "none" | "wrong" | "right" = "none";

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          // Trimmed from 3 -> 1.9 screens -- same issue as Movement 1:
          // once the correction lands, the pin was holding several extra
          // scrolls with nothing changing before releasing into the next
          // movement.
          end: `+=${window.innerHeight * 1.9}`,
          scrub: true,
          pin: true,
          onUpdate: (self) => {
            const p = self.progress;
            if (p > 0.15 && p < 0.55 && beat !== "wrong") {
              beat = "wrong";
              gsap.to(wrongText, { opacity: 1, duration: 0.7, ease: "power1.out" });
              gsap.to(rightText, { opacity: 0, duration: 0.5, ease: "power1.out" });
            } else if (p >= 0.55 && beat !== "right") {
              beat = "right";
              gsap.to(wrongText, { opacity: 0, duration: 0.5, ease: "power1.out" });
              gsap.to(rightText, {
                opacity: 1,
                duration: 0.7,
                delay: 0.2,
                ease: "power1.out",
              });
            } else if (p <= 0.15 && beat !== "none") {
              beat = "none";
              gsap.to(wrongText, { opacity: 0, duration: 0.5, ease: "power1.out" });
              gsap.to(rightText, { opacity: 0, duration: 0.5, ease: "power1.out" });
            }
          },
        },
      });

      // Phase 1 (0.05 - 0.45): the wrong read -- every cell, including
      // the blanks that just haven't happened yet, flashes red as if
      // null were being treated as 0%.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        const isBlank = cellValues[i] === null;
        tl.to(
          ref.current,
          {
            fill: "#e5484d",
            opacity: isBlank ? 0.55 : 0.85,
            r: 14,
            duration: 0.3,
            ease: "power2.out",
          },
          0.05 + (i / pointRefs.length) * 0.2
        );
      });

      // Phase 2 (0.55 - 0.95): the correction -- blanks recede to a
      // near-invisible neutral grey, real values resolve to their true
      // color on the same retention-percentage scale the dashboard uses.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        const value = cellValues[i];
        tl.to(
          ref.current,
          {
            fill: colorForValue(value),
            opacity: value === null ? 0.12 : 0.9,
            r: value === null ? 8 : 14,
            duration: 0.35,
            ease: "power3.inOut",
          },
          0.55 + (i / pointRefs.length) * 0.25
        );
      });
    }, section);

    // See Movement1Hook.tsx -- the global refresh now lives in page.tsx,
    // after every movement has mounted.
    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    // See Movement1Hook.tsx -- pin:true already creates its own spacer
    // sized to "end" above, so a large static height here was redundant
    // scroll distance causing several extra "stuck" scrolls after the
    // correction finished.
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 h-screen px-6 text-center">
        <p
          ref={wrongTextRef}
          className="absolute inset-0 flex items-center justify-center px-8 font-display text-2xl font-medium text-[#e5484d] sm:text-4xl"
        >
          If blank meant zero, this cohort would look dead.
        </p>
        <p
          ref={rightTextRef}
          className="absolute inset-0 flex items-center justify-center px-8 font-display text-2xl font-medium text-foreground sm:text-4xl"
        >
          It&apos;s not zero. It just hasn&apos;t happened yet.
        </p>
      </div>
    </div>
  );
}
