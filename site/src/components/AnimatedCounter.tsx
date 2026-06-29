"use client";

import { useEffect, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

let countersAnimatedThisSession = false;

function formatValue(value: number, decimals: number, suffix: string) {
  return `${value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}${suffix}`;
}

export function AnimatedCounter({
  value,
  decimals = 0,
  suffix = "",
  durationMs = 1400,
  className = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  durationMs?: number;
  className?: string;
}) {
  const prefersReducedMotion = useReducedMotion();
  const finalDisplay = formatValue(value, decimals, suffix);
  const shouldAnimate =
    !prefersReducedMotion && !countersAnimatedThisSession;

  const [display, setDisplay] = useState(
    shouldAnimate ? formatValue(0, decimals, suffix) : finalDisplay
  );

  useEffect(() => {
    if (!shouldAnimate) {
      setDisplay(finalDisplay);
      return;
    }

    countersAnimatedThisSession = true;
    const controls = animate(0, value, {
      duration: durationMs / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(formatValue(v, decimals, suffix)),
    });
    return () => controls.stop();
  }, [shouldAnimate, value, durationMs, decimals, suffix, finalDisplay]);

  return (
    <span className={`num ${className}`}>
      {display}
    </span>
  );
}
