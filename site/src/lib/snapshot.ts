import snapshotData from "../../data/snapshot.json";

export interface Hero {
  total_users: number;
  total_events: number;
  simulation_months: number;
  avg_stickiness_30d: number;
  median_sessions_per_user: number;
}

export interface DauSeries {
  dates: string[];
  dau: number[];
  wau: number[];
  mau: number[];
  stickiness: (number | null)[];
}

export interface SessionStats {
  total_sessions: number;
  distinct_users: number;
  median_session_duration_sec: number;
  p75_session_duration_sec: number;
  p95_session_duration_sec: number;
  median_sessions_per_user: number;
  p75_sessions_per_user: number;
  p95_sessions_per_user: number;
}

export interface Engagement {
  dau_series: DauSeries;
  session_stats: SessionStats;
}

export interface RetentionHeatmapRow {
  cohort_week: string;
  cohort_size: number;
  values: (number | null)[];
}

export interface RetentionHeatmap {
  cohorts: string[];
  weeks: number[];
  grid: RetentionHeatmapRow[];
}

export interface DayNRetentionRow {
  day_n: number;
  eligible_users: number;
  returned_on_day_n: number;
  bounded_retention_pct: number;
  active_on_or_after_day_n: number;
  unbounded_retention_pct: number;
}

export interface RollingRetentionRow {
  cohort_week: string;
  cohort_size: number;
  active_last_28d: number;
  rolling_28d_retention_pct: number;
}

export interface SegmentRetentionRow {
  breakdown_type: string;
  segment: string;
  day_n: number;
  eligible_users: number;
  retained_users: number;
  retention_pct: number;
}

export interface Retention {
  heatmap: RetentionHeatmap;
  day_n: DayNRetentionRow[];
  rolling_28d: RollingRetentionRow[];
  by_segment: SegmentRetentionRow[];
}

export interface FunnelOverall {
  steps: string[];
  users_reached: number[];
  pct_of_signups: number[];
  pct_of_previous_step: (number | null)[];
}

export interface FunnelByChannelRow {
  acquisition_channel: string;
  signups: number;
  first_view: number;
  pct_first_view: number;
  first_engagement: number;
  pct_first_engagement: number;
  repeat_engagement: number;
  pct_repeat_engagement: number;
  premium_conversion: number;
  pct_premium_conversion: number;
}

export interface Funnel {
  overall: FunnelOverall;
  by_channel: FunnelByChannelRow[];
}

export interface Growth {
  weeks: string[];
  new_users: number[];
  returning_users: number[];
  resurrected_users: number[];
  churned_users: number[];
  quick_ratio: (number | null)[];
}

export interface TopWidgetRow {
  widget_id: number;
  name: string;
  widget_type: string;
  sport: string;
  launch_date: string;
  impressions: number;
  interactions: number;
  completions: number;
  total_points_generated: number;
  engagement_rate_pct: number;
}

export interface ContentByTypeRow {
  widget_type: string;
  category: string;
  impressions: number;
  interactions: number;
  completions: number;
  engagement_rate_pct: number;
  completion_rate_pct: number;
}

export interface Content {
  top_widgets: TopWidgetRow[];
  by_type_category: ContentByTypeRow[];
}

export interface StatResult {
  metric_a: number;
  metric_b: number;
  diff: number;
  relative_lift_pct: number;
  se: number;
  statistic: number;
  p_value: number;
  ci_low: number;
  ci_high: number;
  alpha: number;
  n_a: number;
  n_b: number;
}

export interface Decision {
  recommendation: string;
  reason: string;
  is_significant: boolean;
  is_practical: boolean;
  guardrails_ok: boolean;
}

export interface SegmentResult {
  segment: string;
  result: StatResult;
}

export interface Experiment {
  name: string;
  primary_metric: string;
  primary: StatResult;
  guardrail_metric: string;
  guardrail: StatResult;
  guardrail_ok: boolean;
  required_n_per_arm: number;
  decision: Decision;
  segment_results: SegmentResult[];
  cuped_variance_reduction_pct?: number;
  sequential_peeks?: { look: number; frac_of_data: number; n_a: number; n_b: number; p_value: number; "naive_significant_at_0.05": boolean }[];
  sequential_alphas?: { method: string; look: number; alpha_spent: number }[];
  cohens_d?: number;
}

export interface Experiments {
  feed: Experiment;
  onboarding: Experiment;
  push: Experiment;
}

export interface RecommendationEvalRow {
  method: "cf" | "content" | "hybrid";
  segment: "all" | "warm_only" | "cold_only";
  n_users: number;
  recall_at_10: number;
  ndcg_at_10: number;
}

export interface RecommendationEval {
  summary: RecommendationEvalRow[];
  n_test_users: number;
  n_warm: number;
  n_cold: number;
  catalog_size: number;
}

export interface Snapshot {
  hero: Hero;
  engagement: Engagement;
  retention: Retention;
  funnel: Funnel;
  growth: Growth;
  content: Content;
  experiments: Experiments;
  recommendation_eval: RecommendationEval;
}

export const snapshot = snapshotData as unknown as Snapshot;
