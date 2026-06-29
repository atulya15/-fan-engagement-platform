"use client";

import { useEffect, useState } from "react";

/**
 * The one permanent UI element across Movements 1-6 (Loop 2 / Loop 4) --
 * a thin fill-line, never a label, never a nav. Cheap insurance against
 * scroll-anxiety in an otherwise chrome-less experience.
 */
export function ProgressHairline() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    function onScroll() {
      const doc = document.documentElement;
      const max = doc.scrollHeight - doc.clientHeight;
      setProgress(max > 0 ? window.scrollY / max : 0);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="pointer-events-none fixed inset-y-0 right-0 z-50 w-[3px] bg-white/[0.06]">
      <div
        className="w-full bg-white/40"
        style={{ height: `${progress * 100}%` }}
      />
    </div>
  );
}
