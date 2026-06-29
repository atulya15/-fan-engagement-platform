import { AnimatedCounter } from "./AnimatedCounter";

export function StatCard({
  label,
  value,
  suffix = "",
  decimals = 0,
  sublabel,
  accent = false,
}: {
  label: string;
  value: number;
  suffix?: string;
  decimals?: number;
  sublabel?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-hairline bg-surface p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-faint">
        {label}
      </p>
      <p
        className={`mt-2 text-2xl font-semibold sm:text-3xl ${
          accent ? "text-accent" : "text-foreground"
        }`}
      >
        <AnimatedCounter value={value} decimals={decimals} suffix={suffix} />
      </p>
      {sublabel && <p className="mt-1 text-xs text-muted">{sublabel}</p>}
    </div>
  );
}
