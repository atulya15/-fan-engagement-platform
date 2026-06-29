"use client";

import { useField } from "./FieldContext";

/**
 * The persistent engine behind "no hard cuts, same element survives
 * every transition" (Loop 2/5). One fixed-position SVG, one pulse path,
 * one set of point circles -- never unmounted across Movements 1-6.
 * Movement components retarget these same elements via GSAP, they never
 * render their own competing shapes.
 */
export function MorphField() {
  const { pulsePathRef, pointRefs } = useField();

  return (
    <svg
      aria-hidden
      className="pointer-events-none fixed inset-0 z-10 h-full w-full"
      viewBox="0 0 1000 1000"
      // "slice" scales to COVER the viewport, cropping whatever
      // dimension overflows -- on a typical wide desktop window
      // (~16:9), that crops out roughly the top/bottom ~22% of this
      // square viewBox, which is exactly where content positioned near
      // y=850-950 (e.g. Movement 4's final clusters) lives. "meet"
      // scales to FIT entirely within the viewport instead (letterboxed
      // if the aspect ratio doesn't match) -- nothing is ever cropped,
      // which matters more here than filling every pixel edge-to-edge.
      preserveAspectRatio="xMidYMid meet"
    >
      <path
        ref={pulsePathRef}
        d="M 80 500 L 280 500 L 320 380 L 400 660 L 460 320 L 500 500 L 920 500"
        fill="none"
        stroke="#ededef"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0}
      />
      {pointRefs.map((ref, i) => (
        <circle
          key={i}
          ref={ref}
          cx="500"
          cy="500"
          r="4"
          fill="#5e6ad2"
          opacity={0}
        />
      ))}
    </svg>
  );
}
