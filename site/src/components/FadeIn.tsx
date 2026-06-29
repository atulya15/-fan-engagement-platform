import { ReactNode } from "react";

/** Static wrapper — routed dashboard pages render instantly on nav (no enter replay). */
export function FadeIn({
  children,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}
