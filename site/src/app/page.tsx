"use client";

import { useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLenis } from "@/lib/scroll/useLenis";
import { FieldProvider } from "@/components/cinematic/FieldContext";
import { MorphField } from "@/components/cinematic/MorphField";
import { ProgressHairline } from "@/components/cinematic/ProgressHairline";
import { Movement1Hook } from "@/components/cinematic/Movement1Hook";
import { Movement2Retention } from "@/components/cinematic/Movement2Retention";
import { Movement3Funnel } from "@/components/cinematic/Movement3Funnel";
import { Movement4Experiments } from "@/components/cinematic/Movement4Experiments";
import { Movement5Recommendations } from "@/components/cinematic/Movement5Recommendations";
import { Movement6Scale } from "@/components/cinematic/Movement6Scale";
import { Movement7Dashboard } from "@/components/cinematic/Movement7Dashboard";

gsap.registerPlugin(ScrollTrigger);

export default function CinematicHome() {
  useLenis();

  // A single, centralized refresh after every movement below has
  // mounted and created its own ScrollTrigger/pin-spacer. Each movement
  // previously scheduled its own deferred refresh independently, which
  // raced against sibling movements still mounting -- ScrollTrigger
  // could measure a movement's start/end before the full pin-spacer
  // stack existed, computing wrong values (this is what let Movement
  // 3's funnel walls leak into view during Movement 1: an early,
  // incomplete refresh momentarily made Movement 3 measure as already
  // active). Effects fire children-before-parent, so by the time THIS
  // effect runs, every movement's ScrollTrigger already exists.
  useEffect(() => {
    const id = requestAnimationFrame(() => ScrollTrigger.refresh());
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <FieldProvider>
      <main className="relative bg-base">
        <MorphField />
        <ProgressHairline />

        <Movement1Hook />
        <Movement2Retention />
        <Movement3Funnel />
        <Movement4Experiments />
        <Movement5Recommendations />
        <Movement6Scale />
        <Movement7Dashboard />
      </main>
    </FieldProvider>
  );
}
