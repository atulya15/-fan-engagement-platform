"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useField } from "./FieldContext";
import { resyncLenis } from "@/lib/scroll/useLenis";
import { Sidebar } from "@/components/Sidebar";
import { BackgroundArt } from "@/components/BackgroundArt";
import DashboardHome from "@/app/(dashboard)/dashboard/page";

gsap.registerPlugin(ScrollTrigger);

// Movement 6 leaves the shared path drawn as this exact zigzag, centered
// in the 1000x1000 viewBox. This movement shrinks the SAME path down
// into a small mark in the corner -- echoing Sidebar.tsx's real
// PulseMark icon (d="M5 17h4l2.5-7 4 14 3-11 2 4h6.5") closely enough
// that the cut to the real one, moments later, barely reads as a cut.
const SMALL_MARK_D = "M 30 75 L 50 75 L 60 50 L 75 100 L 85 35 L 95 75 L 130 75";

export function Movement7Dashboard() {
  const { pulsePathRef, pointRefs } = useField();
  const sectionRef = useRef<HTMLDivElement>(null);
  const wordmarkRef = useRef<HTMLDivElement>(null);
  const [showDashboard, setShowDashboard] = useState(false);

  // The dashboard mounting adds a large chunk of height well after Lenis
  // and ScrollTrigger already measured the document -- see useLenis.ts's
  // resyncLenis for why that silently clamps further scroll without
  // this. Runs after the new content has actually painted.
  useEffect(() => {
    if (!showDashboard) return;
    const id = requestAnimationFrame(() => resyncLenis());
    return () => cancelAnimationFrame(id);
  }, [showDashboard]);

  useEffect(() => {
    const section = sectionRef.current;
    const path = pulsePathRef.current;
    const wordmark = wordmarkRef.current;
    if (!section || !path || !wordmark) return;

    const ctx = gsap.context(() => {
      gsap.set(wordmark, { opacity: 0 });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: `+=${window.innerHeight * 1.6}`,
          scrub: true,
          pin: true,
          onLeave: () => setShowDashboard(true),
          onEnterBack: () => setShowDashboard(false),
        },
      });

      // Any cohort points still lingering from Movement 6 finish fading
      // out -- past this point the only surviving element is the path
      // itself, becoming the literal logo.
      pointRefs.forEach((ref) => {
        if (ref.current) tl.to(ref.current, { opacity: 0, duration: 0.1 }, 0);
      });

      // Phase 0 (0 - 0.45): the big pulse line shrinks and slides into
      // the corner, becoming a small mark -- the same device Movement 1
      // opened with, now literally turning into a UI element.
      tl.to(
        path,
        { attr: { d: SMALL_MARK_D }, strokeWidth: 5, duration: 0.45, ease: "power2.inOut" },
        0
      );

      // Phase 1 (0.4 - 0.65): "Pulse" fades in beside the mark, exactly
      // mirroring Sidebar.tsx's real Brand layout.
      tl.to(wordmark, { opacity: 1, duration: 0.25, ease: "power1.out" }, 0.4);

      // Phase 2 (0.7 - 0.85): hold -- let the new logo register before
      // the cut.
      // Phase 3 (0.85 - 1.0): the whole cinematic overlay fades out:
      // onLeave (above) swaps in the real dashboard underneath at the
      // same moment, so the fade reveals the real Sidebar's own
      // PulseMark sitting in the exact same corner -- the hand-off.
      tl.to([path, wordmark], { opacity: 0, duration: 0.3, ease: "power1.in" }, 0.85);
    }, section);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs are stable identities, intentionally not re-running
  }, []);

  return (
    <>
      <div ref={sectionRef} className="relative h-screen">
        <div className="pointer-events-none sticky top-0 z-20 h-screen px-6">
          <div
            ref={wordmarkRef}
            className="absolute left-9 top-9 flex items-center gap-2.5"
          >
            <div className="h-8 w-8" />
            <div>
              <p className="font-display text-lg font-semibold leading-tight text-foreground">
                Pulse
              </p>
              <p className="text-[11px] leading-tight text-faint">
                Fan Engagement Analytics
              </p>
            </div>
          </div>
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <p className="font-display text-2xl font-medium text-foreground sm:text-4xl">
              Every story above is one chart below.
            </p>
            <p className="max-w-md text-muted">
              Scroll-jacking ends here -- what follows is the real,
              explorable dashboard.
            </p>
          </div>
        </div>
      </div>

      {/* Deliberately a SIBLING of sectionRef above, not a child of it --
          GSAP's pin:true takes the pinned element (and everything nested
          inside it) out of normal flow via position:fixed, so any
          content placed inside sectionRef would never contribute to the
          document's scrollable height no matter how tall it grows.
          Scroll-jacking permanently releases here: everything below is
          normal document flow, no pin, no scrub -- the same real
          dashboard route reassembled inline, not a recreation of it. */}
      {showDashboard && (
        <div className="relative z-20">
          <BackgroundArt />
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 pt-16 lg:pl-64 lg:pt-0">
              <DashboardHome />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
