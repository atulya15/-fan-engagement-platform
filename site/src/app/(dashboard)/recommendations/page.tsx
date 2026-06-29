import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Section, Card } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { RecommendationEvalChart } from "@/components/RecommendationEvalChart";
import { RecommendationDemo } from "@/components/RecommendationDemo";

export default function RecommendationsPage() {
  const { recommendation_eval } = snapshot;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Recommendations"
        title="Collaborative filtering vs. content-based vs. hybrid"
        insight={`Pure collaborative filtering goes completely blind on cold-start users (0% recall, ${recommendation_eval.n_cold} of ${recommendation_eval.n_test_users} test users) — the hybrid model degrades gracefully instead. Catalog is ${recommendation_eval.catalog_size} widgets, so absolute Recall@10 values aren't directly comparable to production-scale recommenders; the methodology and the cold-start gap are the point.`}
      />

      <Section
        eyebrow="Offline evaluation"
        title="Recall@10 by method and user segment"
        insight="Evaluated on a temporal (not random) train/test split — the model never sees a user's future interactions during training."
      >
        <FadeIn>
          <Card>
            <RecommendationEvalChart evalData={recommendation_eval} />
          </Card>
        </FadeIn>
      </Section>

      <Section
        eyebrow="Raw numbers"
        title="Recall@10 and NDCG@10 by method"
      >
        <FadeIn>
          <Card>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="border-b border-hairline text-left text-faint">
                    <th className="py-2 pr-6 font-medium">Method</th>
                    <th className="py-2 pr-6 font-medium">Segment</th>
                    <th className="py-2 pr-6 font-medium">Users</th>
                    <th className="py-2 pr-6 font-medium">Recall@10</th>
                    <th className="py-2 font-medium">NDCG@10</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation_eval.summary.map((row, i) => (
                    <tr key={i} className="border-b border-hairline/50">
                      <td className="py-2 pr-6 capitalize text-foreground">
                        {row.method}
                      </td>
                      <td className="py-2 pr-6 text-muted">
                        {row.segment.replace(/_/g, " ")}
                      </td>
                      <td className="py-2 pr-6 text-muted">{row.n_users}</td>
                      <td className="py-2 pr-6 text-accent">
                        {(row.recall_at_10 * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 text-accent">
                        {(row.ndcg_at_10 * 100).toFixed(1)}%
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
        eyebrow="Live demo"
        title="Try the deployed recommender"
        insight="Calls the deployed FastAPI hybrid recommender directly from your browser — the one part of this site that isn't precomputed."
      >
        <FadeIn>
          <RecommendationDemo />
        </FadeIn>
      </Section>
    </PageContainer>
  );
}
