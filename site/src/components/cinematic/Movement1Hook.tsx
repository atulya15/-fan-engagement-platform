"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField, FIELD_COLUMNS, FIELD_ROWS } from "./FieldContext";

// Registered at module scope, not inside an effect. useLenis() also
// registers this plugin, but inside ITS OWN effect on the parent page
// component -- and React fires a child component's effects before its
// parent's, so Movement1Hook's effect was running before that
// registration ever happened. Without the plugin registered, GSAP
// silently treats `scrollTrigger: {...}` as an invalid animatable
// property and just plays the timeline immediately, ungated by scroll
// at all -- which is what every "it all happens instantly" symptom this
// session traced back to. Module-scope registration runs at import
// time, before any component effect, and gsap.registerPlugin is a
// no-op on repeat calls so this is safe alongside useLenis's call too.
gsap.registerPlugin(ScrollTrigger);

const GRID_X0 = 150;
const GRID_X1 = 850;
const GRID_Y0 = 200;
const GRID_Y1 = 800;

function gridPosition(index: number) {
  const col = index % FIELD_COLUMNS;
  const row = Math.floor(index / FIELD_COLUMNS);
  const x = GRID_X0 + (col / (FIELD_COLUMNS - 1)) * (GRID_X1 - GRID_X0);
  const y = GRID_Y0 + (row / (FIELD_ROWS - 1)) * (GRID_Y1 - GRID_Y0);
  return { x, y };
}

export function Movement1Hook() {
  const { pulsePathRef, pointRefs } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const hookTextRef = useRef<HTMLParagraphElement>(null);
  const scaleTextRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const path = pulsePathRef.current;
    const section = sectionRef.current;
    const hookText = hookTextRef.current;
    const scaleText = scaleTextRef.current;
    if (!path || !section || !hookText || !scaleText) return;

    // gsap.context is the official React-safe pattern: every tween and
    // ScrollTrigger created inside it is tracked automatically, and
    // ctx.revert() on cleanup fully tears all of it down AND restores
    // pre-animation inline styles -- this is what fixed the earlier
    // "scrolling back up does nothing" bug.
    //
    // The headline crossfade is animated directly on these refs as part
    // of THIS SAME timeline, rather than bridged through React state via
    // an onUpdate callback -- the earlier version did that, and the
    // state update never visibly landed in sync with the rest of the
    // choreography. Keeping it inside one GSAP timeline removes that
    // entire class of bug: there's nothing left to desync from.
    const ctx = gsap.context(() => {
      const length = path.getTotalLength();
      gsap.set(path, {
        strokeDasharray: length,
        strokeDashoffset: length,
        opacity: 0,
      });
      pointRefs.forEach((ref) => {
        if (ref.current) {
          gsap.set(ref.current, { cx: 500, cy: 500, r: 4, opacity: 0 });
        }
      });
      gsap.set(hookText, { opacity: 1 });
      gsap.set(scaleText, { opacity: 0 });

      // Scatter targets are computed once, fixed per point -- so the
      // "multiply" burst always fans out to the same shape rather than
      // re-randomizing on every scroll direction change.
      const scatterTargets = pointRefs.map(() => ({
        x: 200 + Math.random() * 600,
        y: 150 + Math.random() * 700,
      }));

      // The headline crossfade is deliberately NOT part of the scrubbed
      // timeline below. A scrubbed tween has no time dimension of its
      // own -- its speed is dictated entirely by how fast the scroll
      // position changes, so on a fast wheel/trackpad it always resolves
      // in well under a second no matter how much scroll distance the
      // section is given. Triggering it as an independent, fixed-duration
      // tween (real seconds, not scroll-mapped) the first time scroll
      // crosses the halfway point fixes that permanently: the crossfade
      // always takes ~1.3s of wall-clock time regardless of scroll speed.
      let headlineState: "hook" | "scale" = "hook";

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          // A percentage "end" is relative to the TRIGGER element's own
          // height (this section is h-[300vh]), not the viewport -- so
          // "+=350%" was actually ~10.5 viewport-heights of scroll, far
          // more than intended and the likely reason the crossfade
          // threshold became unreachable within normal scrolling. Using
          // an explicit viewport-relative pixel value removes that
          // ambiguity. Trimmed from 3.5 -> 2.2 screens: the settle phase
          // was finishing well before the pin released, leaving several
          // scrolls of "nothing new happening" before Movement 2 began.
          // The headline crossfade timing is unaffected -- it's an
          // independent, fixed-duration tween, not scroll-distance-based.
          // (Computed directly, not via a function -- this effect only
          // ever runs client-side, so window is always available here.)
          end: `+=${window.innerHeight * 2.2}`,
          scrub: true,
          pin: true,
          onUpdate: (self) => {
            if (self.progress > 0.5 && headlineState === "hook") {
              headlineState = "scale";
              gsap.to(hookText, { opacity: 0, duration: 0.9, ease: "power1.out" });
              gsap.to(scaleText, {
                opacity: 1,
                duration: 0.9,
                delay: 0.35,
                ease: "power1.out",
              });
            } else if (self.progress <= 0.5 && headlineState === "scale") {
              headlineState = "hook";
              gsap.to(scaleText, { opacity: 0, duration: 0.9, ease: "power1.out" });
              gsap.to(hookText, {
                opacity: 1,
                duration: 0.9,
                delay: 0.35,
                ease: "power1.out",
              });
            }
          },
        },
      });

      // Phase 1 (0 - 0.12): draw the pulse line. Headline is locked on
      // the hook line and does not move yet.
      tl.to(path, { strokeDashoffset: 0, opacity: 1, ease: "none", duration: 0.12 });

      // Phase 2 (0.12 - 0.5): multiply -- points fade in and scatter
      // outward, *while the hook line is still held on screen*. This is
      // the long hold the headline crossfade was missing.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        tl.to(
          ref.current,
          {
            opacity: 0.55,
            cx: scatterTargets[i].x,
            cy: scatterTargets[i].y,
            duration: 0.3,
            ease: "power2.out",
          },
          0.12 + (i / pointRefs.length) * 0.3
        );
      });

      // Phase 3 (0.7 - 1.0): settle -- points condense into the grid that
      // Movement 2 (retention) will resolve into real data.
      pointRefs.forEach((ref, i) => {
        if (!ref.current) return;
        const target = gridPosition(i);
        tl.to(
          ref.current,
          {
            opacity: 0.85,
            cx: target.x,
            cy: target.y,
            r: 6,
            duration: 0.4,
            ease: "power3.inOut",
          },
          0.7 + (i / pointRefs.length) * 0.15
        );
      });

      // Fade the original pulse path out as the field takes over.
      tl.to(path, { opacity: 0, duration: 0.15 }, 0.6);
    }, section);

    // The global refresh (after every movement has mounted) lives in
    // page.tsx now -- each movement scheduling its OWN deferred refresh
    // independently raced against its siblings still mounting, which
    // could make ScrollTrigger briefly measure a movement's position
    // before the page's full pin-spacer stack existed yet, causing
    // wrong start/end values (and, for movements that gate setup on
    // onEnter/isActive, a false-positive "already active" misfire).
    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    // GSAP's pin:true already creates its own spacer sized to "end"
    // above -- a large static height here is REDUNDANT scroll distance
    // on top of that, and is exactly what was producing several extra
    // "stuck" scrolls after the sequence finished (the sticky headline
    // keeps clinging to the top of the viewport for the section's own
    // natural height, even after GSAP's pin has already released).
    <div ref={sectionRef} className="relative h-screen">
      <div className="pointer-events-none sticky top-0 z-20 h-screen px-6 text-center">
        <p
          ref={hookTextRef}
          className="absolute inset-0 flex items-center justify-center font-display text-3xl font-medium text-foreground sm:text-5xl"
        >
          Every interaction tells a story.
        </p>
        <div
          ref={scaleTextRef}
          className="absolute inset-0 flex flex-col items-center justify-center"
        >
          <p className="num text-4xl font-semibold text-foreground sm:text-6xl">
            10,000 fans
          </p>
          <p className="num mt-3 text-lg text-muted sm:text-2xl">
            2,000,000 moments of attention, won or lost.
          </p>
        </div>
      </div>
    </div>
  );
}
