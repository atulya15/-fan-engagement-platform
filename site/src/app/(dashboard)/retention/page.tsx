import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Section, Card } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { RetentionHeatmap } from "@/components/RetentionHeatmap";

export default function RetentionPage() {
  const { retention } = snapshot;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Retention"
        title="Weekly cohort retention"
        insight="The single most interview-scrutinized part of any product analytics layer — every metric below is explicit about bounded ('returned ON day N') vs. unbounded ('active ON OR AFTER day N') retention, since conflating them is the most common subtle bug in this space."
      />

      <Section
        eyebrow="Cohort heatmap"
        title="Signup-week cohort × weeks since signup"
        insight="Blank cells are cohorts too young to have reached that week yet — censored, not zero. This distinction was a real bug caught and fixed during this project's build (see the README design notes)."
      >
        <FadeIn>
          <RetentionHeatmap retention={retention.heatmap} />
        </FadeIn>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section eyebrow="Day-N retention" title="Bounded vs. unbounded">
          <FadeIn>
            <Card>
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 font-medium">Day</th>
                    <th className="py-2 font-medium">Eligible</th>
                    <th className="py-2 font-medium">Bounded</th>
                    <th className="py-2 font-medium">Unbounded</th>
                  </tr>
                </thead>
                <tbody>
                  {retention.day_n.map((row) => (
                    <tr key={row.day_n} className="border-b border-hairline/50">
                      <td className="py-2 text-foreground">D{row.day_n}</td>
                      <td className="py-2 text-muted">
                        {row.eligible_users.toLocaleString("en-US")}
                      </td>
                      <td className="py-2 text-foreground">
                        {row.bounded_retention_pct.toFixed(1)}%
                      </td>
                      <td className="py-2 text-accent">
                        {row.unbounded_retention_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </FadeIn>
        </Section>

        <Section
          eyebrow="Rolling health"
          title="28-day rolling retention by cohort"
          insight="% of each cohort active at any point in the trailing 28 days — catches cohorts that retained early but have since gone dormant."
        >
          <FadeIn>
            <Card className="max-h-96 overflow-y-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 font-medium">Cohort</th>
                    <th className="py-2 font-medium">Size</th>
                    <th className="py-2 font-medium">Active (28d)</th>
                    <th className="py-2 font-medium">Rolling %</th>
                  </tr>
                </thead>
                <tbody>
                  {retention.rolling_28d.slice(-20).reverse().map((row) => (
                    <tr key={row.cohort_week} className="border-b border-hairline/50">
                      <td className="py-2 text-foreground">{row.cohort_week}</td>
                      <td className="py-2 text-muted">{row.cohort_size}</td>
                      <td className="py-2 text-muted">{row.active_last_28d}</td>
                      <td className="py-2 text-accent">
                        {row.rolling_28d_retention_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </FadeIn>
        </Section>
      </div>

      <Section
        eyebrow="Segment breakdown"
        title="Retention by acquisition channel & device"
        insight="Day-7 / Day-30 unbounded retention split by segment — reveals whether one acquisition source brings in users who stick around, independent of overall volume."
      >
        <FadeIn>
          <Card>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 pr-6 font-medium">Type</th>
                    <th className="py-2 pr-6 font-medium">Segment</th>
                    <th className="py-2 pr-6 font-medium">Day</th>
                    <th className="py-2 pr-6 font-medium">Eligible</th>
                    <th className="py-2 font-medium">Retention</th>
                  </tr>
                </thead>
                <tbody>
                  {retention.by_segment.map((row, i) => (
                    <tr key={i} className="border-b border-hairline/50">
                      <td className="py-2 pr-6 capitalize text-muted">
                        {row.breakdown_type}
                      </td>
                      <td className="py-2 pr-6 text-foreground">{row.segment}</td>
                      <td className="py-2 pr-6 text-muted">D{row.day_n}</td>
                      <td className="py-2 pr-6 text-muted">
                        {row.eligible_users.toLocaleString("en-US")}
                      </td>
                      <td className="py-2 text-accent">
                        {row.retention_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </FadeIn>
      </Section>
    </PageContainer>
  );
}
