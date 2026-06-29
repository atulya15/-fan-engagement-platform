"use client";

import { createContext, useContext, useMemo, useRef, RefObject } from "react";

// Matches the real retention heatmap's dimensions (14 visible cohorts x
// 12 weeks -- see RetentionHeatmap.tsx's VISIBLE_COHORTS) so the "field
// of fans" point count Movement 1 multiplies into is the same grid
// Movement 2 will later resolve into real data, not an arbitrary number.
export const FIELD_COLUMNS = 12;
export const FIELD_ROWS = 14;
export const FIELD_POINT_COUNT = FIELD_COLUMNS * FIELD_ROWS;

interface FieldContextValue {
  pulsePathRef: RefObject<SVGPathElement | null>;
  pointRefs: RefObject<SVGCircleElement | null>[];
}

const FieldContext = createContext<FieldContextValue | null>(null);

export function FieldProvider({ children }: { children: React.ReactNode }) {
  const pulsePathRef = useRef<SVGPathElement | null>(null);
  // eslint-disable-next-line react-hooks/rules-of-hooks -- stable count, not a loop-dependent hook call
  const pointRefs = useMemo(
    () =>
      Array.from({ length: FIELD_POINT_COUNT }, () => ({
        current: null,
      })) as RefObject<SVGCircleElement | null>[],
    []
  );

  return (
    <FieldContext.Provider value={{ pulsePathRef, pointRefs }}>
      {children}
    </FieldContext.Provider>
  );
}

export function useField() {
  const ctx = useContext(FieldContext);
  if (!ctx) throw new Error("useField must be used within FieldProvider");
  return ctx;
}
