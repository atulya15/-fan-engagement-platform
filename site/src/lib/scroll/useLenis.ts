"use client";

import { useEffect } from "react";
import Lenis from "lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

let registered = false;
let activeLenis: Lenis | null = null;

// Lenis caches the document's scrollable height at init via a
// ResizeObserver on documentElement -- which fires on viewport resize,
// but NOT when content already in the DOM grows taller without the
// viewport itself changing size (e.g. Movement7Dashboard.tsx mounting
// the real dashboard underneath the cinematic hand-off well after
// Lenis booted). Without calling this afterward, Lenis's internal
// scroll limit stays stuck at the pre-mount document height and
// silently clamps all further scroll input at that old boundary.
export function resyncLenis() {
  activeLenis?.resize();
  ScrollTrigger.refresh();
}

/**
 * Drives Lenis's smooth-scroll RAF loop through GSAP's ticker instead of
 * its own, and tells ScrollTrigger to re-measure on every Lenis scroll
 * event. Without this wiring, Lenis's damped scroll position and
 * ScrollTrigger's pin/scrub math drift out of sync within seconds.
 */
export function useLenis() {
  useEffect(() => {
    // The browser restores the previous scroll position on refresh by
    // default. Lenis always boots at 0 and then smoothly (lerp) catches
    // up to wherever the browser put native scrollY -- on a page you'd
    // last scrolled deep into, that produces a ~1s animated "jump"
    // through the whole timeline with no actual scrolling, which is
    // exactly the symptom reported here. A cinematic, narrative page
    // should always start clean at the top on load regardless.
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual";
    }
    window.scrollTo(0, 0);

    if (!registered) {
      gsap.registerPlugin(ScrollTrigger);
      registered = true;
    }

    const lenis = new Lenis({
      lerp: 0.1,
      wheelMultiplier: 1,
    });
    lenis.scrollTo(0, { immediate: true });

    lenis.on("scroll", ScrollTrigger.update);
    activeLenis = lenis;

    const onTick = (time: number) => {
      lenis.raf(time * 1000);
    };
    gsap.ticker.add(onTick);
    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.destroy();
      activeLenis = null;
      gsap.ticker.remove(onTick);
    };
  }, []);
}
