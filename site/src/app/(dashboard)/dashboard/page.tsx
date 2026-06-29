import Link from "next/link";
import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Card } from "@/components/Section";
import { StatCard } from "@/components/StatCard";
import { DauChart } from "@/components/DauChart";
import { FadeIn } from "@/components/FadeIn";

export default function Home() {
  const { hero, engagement, retention, funnel, growth, experiments, recommendation_eval } =
    snapshot;

  const latestQuickRatio = growth.quick_ratio.filter((v) => v !== null).at(-1) ?? 0;
  const leakIndex = funnel.overall.pct_of_previous_step
    .map((v, i) => ({ i, v }))
    .filter((d) => d.v !== null)
    .reduce((min, d) => (d.v! < min.v! ? d : min), { i: -1, v: 101 }).i;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Overview"
        title="Pulse — Fan Engagement Analytics"
        insight="A simulated LiveLike-style sports & media gamification product — polls, trivia, predictions, leaderboards — instrumented end-to-end with retention analysis, A/B experimentation, and a hybrid recommendation engine. 10K simulated users, 12 months, ~2M events."
      />

      <FadeIn>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Simulated users" value={hero.total_users} />
          <StatCard label="Widget events" value={hero.total_events} />
          <StatCard
            label="DAU/MAU stickiness"
            value={hero.avg_stickiness_30d * 100}
            decimals={1}
            suffix="%"
            accent
          />
          <StatCard
            label="Median sessions / user"
            value={hero.median_sessions_per_user}
          />
        </div>
      </FadeIn>

      <FadeIn delay={0.05} className="mt-6">
        <Card>
          <div className="mb-4 flex items-baseline justify-between">
            <p className="text-sm font-medium text-foreground">
              Daily / weekly / monthly active users
            </p>
            <p className="text-xs text-muted">
              {engagement.session_stats.total_sessions.toLocaleString("en-US")} sessions ·{" "}
              {engagement.session_stats.distinct_users.toLocaleString("en-US")} users
            </p>
          </div>
          <DauChart series={engagement.dau_series} />
        </Card>
      </FadeIn>

      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        <FadeIn delay={0.1}>
          <PreviewCard
            href="/retention"
            eyebrow="Retention"
            title="Cohort retention heatmap"
            metric={`${retention.heatmap.cohorts.length} weekly cohorts`}
            description="Bounded vs. unbounded Day-N retention, rolling 28-day health, and segment breakdowns."
          />
        </FadeIn>
        <FadeIn delay={0.13}>
          <PreviewCard
            href="/funnels"
            eyebrow="Funnels"
            title="Signup-to-premium funnel"
            metric={`Biggest leak: step ${leakIndex + 1}`}
            description="Overall and step-over-step conversion, plus a per-channel breakdown."
          />
        </FadeIn>
        <FadeIn delay={0.16}>
          <PreviewCard
            href="/growth"
            eyebrow="Growth"
            title="New, returning & resurrected"
            metric={`Quick Ratio: ${latestQuickRatio?.toFixed(2)}`}
            description="Weekly growth composition, churn, and widget/content performance."
          />
        </FadeIn>
        <FadeIn delay={0.19}>
          <PreviewCard
            href="/experiments"
            eyebrow="Experimentation"
            title="3 A/B tests, full stats"
            metric={`${experiments.push.decision.recommendation} on push timing`}
            description="Lift, CI, CUPED variance reduction, sequential-peeking demo, and ship decisions."
          />
        </FadeIn>
        <FadeIn delay={0.22}>
          <PreviewCard
            href="/recommendations"
            eyebrow="Recommendations"
            title="CF vs. content vs. hybrid"
            metric={`${recommendation_eval.catalog_size}-widget catalog`}
            description="Cold-start comparison plus a live recommendation demo against the deployed API."
          />
        </FadeIn>
        <FadeIn delay={0.25}>
          <a
            href="https://github.com/atulya15/-fan-engagement-platform"
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-full cursor-pointer flex-col justify-between rounded-2xl border border-dashed border-hairline-strong p-6 transition-colors hover:bg-surface"
          >
            <div>
              <p className="num text-xs font-medium uppercase tracking-wide text-faint">
                Source
              </p>
              <p className="mt-2 font-display text-lg font-semibold text-foreground">
                Read the code
              </p>
              <p className="mt-2 text-sm text-muted">
                Schema, data generator, metrics SQL, experimentation engine,
                and recommendation models — all on GitHub.
              </p>
            </div>
            <span className="mt-4 text-sm text-accent">View repository →</span>
          </a>
        </FadeIn>
      </div>
    </PageContainer>
  );
}

function PreviewCard({
  href,
  eyebrow,
  title,
  metric,
  description,
}: {
  href: string;
  eyebrow: string;
  title: string;
  metric: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="flex h-full cursor-pointer flex-col justify-between rounded-2xl border border-hairline bg-surface p-6 transition-colors hover:bg-surface-hover"
    >
      <div>
        <p className="num text-xs font-medium uppercase tracking-wide text-accent">
          {eyebrow}
        </p>
        <p className="mt-2 font-display text-lg font-semibold text-foreground">
          {title}
        </p>
        <p className="num mt-2 text-sm text-foreground">{metric}</p>
        <p className="mt-2 text-sm text-muted">{description}</p>
      </div>
      <span className="mt-4 text-sm text-accent">Explore →</span>
    </Link>
  );
}
