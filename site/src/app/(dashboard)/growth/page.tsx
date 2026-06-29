import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Section, Card } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { GrowthChartView } from "@/components/GrowthChart";

export default function GrowthPage() {
  const { growth, content } = snapshot;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Growth"
        title="New, returning & resurrected users"
        insight="Quick Ratio = (new + resurrected) ÷ churned. Above 1.0 means the platform gained more users that week than it lost to churn — net growth, not just vanity top-of-funnel acquisition hiding a leaky bottom."
      />

      <Section
        eyebrow="Weekly growth composition"
        title="User composition & Quick Ratio over time"
        insight="Quick Ratio stays above the breakeven line for most of the simulation — the dashed red line tracks churned users for direct comparison against the stacked gains."
      >
        <FadeIn>
          <Card>
            <GrowthChartView growth={growth} />
          </Card>
        </FadeIn>
      </Section>

      <Section
        eyebrow="Content performance"
        title="Top widgets by engagement rate"
        insight="The widget-level analog to creator performance — this product has no creator_id, so the individual widget is the unit of 'a piece of content.' Filtered to widgets with enough impressions to rank reliably."
      >
        <FadeIn>
          <Card>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 pr-6 font-medium">Widget</th>
                    <th className="py-2 pr-6 font-medium">Type</th>
                    <th className="py-2 pr-6 font-medium">Sport</th>
                    <th className="py-2 pr-6 font-medium">Impressions</th>
                    <th className="py-2 pr-6 font-medium">Completions</th>
                    <th className="py-2 font-medium">Engagement</th>
                  </tr>
                </thead>
                <tbody>
                  {content.top_widgets.map((row) => (
                    <tr key={row.widget_id} className="border-b border-hairline/50">
                      <td className="py-2 pr-6 text-foreground">{row.name}</td>
                      <td className="py-2 pr-6 capitalize text-muted">
                        {row.widget_type}
                      </td>
                      <td className="py-2 pr-6 text-muted">{row.sport}</td>
                      <td className="py-2 pr-6 text-muted">
                        {row.impressions.toLocaleString("en-US")}
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.completions.toLocaleString("en-US")}
                      </td>
                      <td className="py-2 text-accent">
                        {row.engagement_rate_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </FadeIn>
      </Section>

      <Section
        eyebrow="Format × category"
        title="Engagement by widget type and sport"
        insight="Whether a format works depends on which content category it's paired with, not just the format alone."
      >
        <FadeIn>
          <Card>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 pr-6 font-medium">Type</th>
                    <th className="py-2 pr-6 font-medium">Category</th>
                    <th className="py-2 pr-6 font-medium">Engagement rate</th>
                    <th className="py-2 font-medium">Completion rate</th>
                  </tr>
                </thead>
                <tbody>
                  {content.by_type_category.map((row, i) => (
                    <tr key={i} className="border-b border-hairline/50">
                      <td className="py-2 pr-6 capitalize text-foreground">
                        {row.widget_type}
                      </td>
                      <td className="py-2 pr-6 text-muted">{row.category}</td>
                      <td className="py-2 pr-6 text-accent">
                        {row.engagement_rate_pct.toFixed(1)}%
                      </td>
                      <td className="py-2 text-accent">
                        {row.completion_rate_pct.toFixed(1)}%
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
