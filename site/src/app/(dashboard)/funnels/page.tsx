import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Section, Card } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { FunnelChartView } from "@/components/FunnelChart";

export default function FunnelsPage() {
  const { funnel } = snapshot;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Funnels"
        title="From signup to premium"
        insight="Reports both overall (% of all signups) and step-over-step (% of the previous step) conversion, since they answer different questions — overall tells you total loss, step-over-step tells you where to fix it."
      />

      <Section
        eyebrow="Core funnel"
        title="Signup → first view → first engagement → repeat engagement → premium"
        insight="The biggest drop isn't onboarding — it's converting a single engagement into a repeat one. That step is highlighted in red."
      >
        <FadeIn>
          <Card>
            <FunnelChartView funnel={funnel.overall} />
          </Card>
        </FadeIn>
      </Section>

      <Section
        eyebrow="By acquisition channel"
        title="Does every channel leak at the same step?"
        insight="Same funnel, broken down by acquisition_channel — reveals whether different channels leak at different funnel stages, which changes where you'd invest fix effort per channel."
      >
        <FadeIn>
          <Card>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 pr-6 font-medium">Channel</th>
                    <th className="py-2 pr-6 font-medium">Signups</th>
                    <th className="py-2 pr-6 font-medium">First view</th>
                    <th className="py-2 pr-6 font-medium">First engagement</th>
                    <th className="py-2 pr-6 font-medium">Repeat engagement</th>
                    <th className="py-2 font-medium">Premium</th>
                  </tr>
                </thead>
                <tbody>
                  {funnel.by_channel.map((row) => (
                    <tr
                      key={row.acquisition_channel}
                      className="border-b border-hairline/50"
                    >
                      <td className="py-2 pr-6 capitalize text-foreground">
                        {row.acquisition_channel.replace(/_/g, " ")}
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.signups.toLocaleString("en-US")}
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.pct_first_view.toFixed(1)}%
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.pct_first_engagement.toFixed(1)}%
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.pct_repeat_engagement.toFixed(1)}%
                      </td>
                      <td className="py-2 text-accent">
                        {row.pct_premium_conversion.toFixed(1)}%
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
