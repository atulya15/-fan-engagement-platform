"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: OverviewIcon },
  { href: "/retention", label: "Retention", icon: RetentionIcon },
  { href: "/funnels", label: "Funnels", icon: FunnelIcon },
  { href: "/growth", label: "Growth", icon: GrowthIcon },
  { href: "/experiments", label: "Experiments", icon: ExperimentIcon },
  { href: "/recommendations", label: "Recommendations", icon: RecommendIcon },
];

const DASHBOARD_URL =
  process.env.NEXT_PUBLIC_DASHBOARD_URL ??
  "https://github.com/atulya15/-fan-engagement-platform";
const REPO_URL = "https://github.com/atulya15/-fan-engagement-platform";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile top bar */}
      <header className="fixed inset-x-0 top-0 z-50 flex items-center justify-between border-b border-hairline bg-base/80 px-5 py-4 backdrop-blur-md lg:hidden">
        <Brand />
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="cursor-pointer rounded-lg border border-hairline px-3 py-1.5 text-sm text-foreground"
        >
          GitHub
        </a>
      </header>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-hairline bg-base/60 backdrop-blur-md lg:flex">
        <div className="px-6 py-7">
          <Brand />
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  active
                    ? "bg-surface text-foreground"
                    : "text-muted hover:bg-surface hover:text-foreground"
                }`}
              >
                <item.icon
                  className={`h-4 w-4 flex-shrink-0 ${
                    active ? "text-accent" : "text-faint group-hover:text-accent"
                  }`}
                />
                {item.label}
                {active && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="space-y-2 border-t border-hairline px-3 py-4">
          <Link
            href="/"
            className="block cursor-pointer rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground"
          >
            ← Back to the story
          </Link>
          <a
            href={DASHBOARD_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="block cursor-pointer rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-foreground"
          >
            Full Streamlit dashboard →
          </a>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="block cursor-pointer rounded-lg border border-hairline px-3 py-2 text-center text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            GitHub
          </a>
        </div>
      </aside>
    </>
  );
}

function Brand() {
  return (
    <Link href="/dashboard" className="flex cursor-pointer items-center gap-2.5">
      <PulseMark />
      <div>
        <p className="font-display text-lg font-semibold leading-tight text-foreground">
          Pulse
        </p>
        <p className="text-[11px] leading-tight text-faint">
          Fan Engagement Analytics
        </p>
      </div>
    </Link>
  );
}

function PulseMark() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8 flex-shrink-0">
      <rect width="32" height="32" rx="9" fill="var(--color-accent)" opacity="0.15" />
      <path
        d="M5 17h4l2.5-7 4 14 3-11 2 4h6.5"
        fill="none"
        stroke="var(--color-accent-bright)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function OverviewIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function RetentionIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 9h18M3 15h18M9 3v18M15 3v18" stroke="currentColor" strokeWidth="1.2" opacity="0.6" />
    </svg>
  );
}

function FunnelIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M3 4h18l-7 9v6l-4 2v-8L3 4z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

function GrowthIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M4 18l5-6 4 3 7-9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M15 6h5v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ExperimentIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function RecommendIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M12 2l2.5 6.5L21 11l-6.5 2.5L12 20l-2.5-6.5L3 11l6.5-2.5L12 2z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}
