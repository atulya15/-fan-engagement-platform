import { snapshot } from "@/lib/snapshot";
import { PageContainer, PageHeader, Section } from "@/components/Section";
import { FadeIn } from "@/components/FadeIn";
import { ExperimentCardView } from "@/components/ExperimentCard";

export default function ExperimentsPage() {
  const { experiments } = snapshot;

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Experimentation"
        title="A/B testing & experimentation engine"
        insight="Three experiments, each assigned at signup, analyzed with the same statistical engine: two-sample tests, guardrail checks, segment breakdowns, and an explicit ship/no-ship decision combining statistical and practical significance."
      />

      <Section
        eyebrow="Experiment A"
        title="Personalized Feed vs. Chronological"
        insight="Primary metric: bounded Day-7 retention. Guardrail: average session duration, to make sure personalization didn't make sessions shallower while chasing a return visit."
      >
        <FadeIn>
          <ExperimentCardView experiment={experiments.feed} />
        </FadeIn>
      </Section>

      <Section
        eyebrow="Experiment B"
        title="Onboarding Steps Reduction"
        insight="Primary metric: signup → first-engagement conversion. Guardrail: completion rate, to make sure a faster path to engagement didn't trade away engagement quality."
      >
        <FadeIn>
          <ExperimentCardView experiment={experiments.onboarding} />
        </FadeIn>
      </Section>

      <Section
        eyebrow="Experiment C"
        title="Push Notification Timing"
        insight="3-arm test (morning / evening / ML-optimized) on total session count, with CUPED variance reduction using acquisition-channel quality as the pre-experiment covariate, plus a sequential-peeking demonstration."
      >
        <FadeIn>
          <ExperimentCardView experiment={experiments.push} />
        </FadeIn>
      </Section>
    </PageContainer>
  );
}
