# Data Dictionary — Fan Engagement Platform

Documents every table and column in the schema (`schema.sql`), and the business
meaning behind each — not just the type. Generated/maintained alongside
`generate_data.py`. If you add a column, add it here in the same PR.

---

## `users`

One row per fan account.

| Column | Type | Business meaning |
|---|---|---|
| `user_id` | `SERIAL PK` | Internal identity. |
| `signup_date` | `TIMESTAMPTZ` | When the account was created. Anchors all retention/cohort math — see [queries.sql §4](queries.sql). |
| `country` | `VARCHAR(100)` | Self-reported / inferred country, used for geo breakdowns. |
| `device_type` | `iOS \| Android \| Web` | Primary device at signup. |
| `user_segment` | `free \| premium \| churned` | **Derived post-hoc from behavior, not assigned at signup.** Computed in `generate_user_segments()`: `churned` = no session in the trailing 45 days of the simulation window; `premium` = not churned, in the top 25% of users by `total_points`, and clears a random 70% conversion check (not every high-engagement user pays — avoids an artificial points→premium cliff); `free` = everyone else. In production this would be recomputed nightly, not fixed at signup. |
| `acquisition_channel` | `organic \| paid_social \| referral \| influencer \| app_store_search` | How the user found the product. Each channel has a different engagement-quality multiplier baked into the generator (`CHANNEL_QUALITY_MULTIPLIER`) — organic/referral users engage ~15% more than the power-law baseline, paid_social/influencer users ~35–45% less. This mirrors a real product reality: cheap paid acquisition is often lower-intent. |

---

## `sessions`

One row per app open. The unit of "a visit."

| Column | Type | Business meaning |
|---|---|---|
| `session_id` | `SERIAL PK` | |
| `user_id` | `FK -> users` | |
| `app_open_time` / `app_close_time` | `TIMESTAMPTZ` | Session bounds. `app_close_time` can be `NULL` if a session is still open (not generated in synthetic data, but the schema allows it for a live system). Session duration = `app_close_time - app_open_time`. |
| `platform` | `iOS \| Android \| Web` | Platform for *this* session — can differ from the user's `device_type` if they use multiple devices. |

---

## `widgets`

One row per gamification widget (a poll, trivia question, prediction, or leaderboard instance) — this is the **content dimension** of the platform.

| Column | Type | Business meaning |
|---|---|---|
| `widget_id` | `SERIAL PK` | |
| `widget_type` | `poll \| trivia \| prediction \| leaderboard` | Drives different impression→interaction→completion conversion rates (see `WIDGET_CONVERSION` in `generate_data.py`) — polls are one-tap and convert ~2x better than leaderboards. |
| `name` | `VARCHAR(150)` | Display name. |
| `sport` | `VARCHAR(50)` | Content category (Football, Cricket, etc.) — drives seasonality/relevance, not used for seasonality simulation yet (stretch goal). |
| `launch_date` | `TIMESTAMPTZ` | When the widget went live. Events can't exist before this — a widget isn't "impressed" before it launches. |

---

## `widget_events`

**The core fact table.** One row per impression / interaction / completion. This is the event stream everything else is computed from.

| Column | Type | Business meaning |
|---|---|---|
| `event_id` | `BIGSERIAL PK` | |
| `widget_id`, `user_id`, `session_id` | `FK`s | The who/what/when-context of the event. |
| `event_type` | `impression \| interaction \| completion` | The funnel stage. `impression` = widget was shown; `interaction` = user tapped/answered/voted; `completion` = the full flow finished (e.g. poll vote registered, trivia answer submitted). |
| `event_timestamp` | `TIMESTAMPTZ` | When it happened — always within the parent session's open/close window. |
| `points_earned` | `INTEGER` | Gamification points awarded for this specific event (`impression`=0, `interaction`=1, `completion`=5). Rolls up into `user_points.total_points`. |
| `properties` | `JSONB` | Flexible per-event metadata, varying by `widget_type` — e.g. `{"choice": "B"}` for a poll interaction, `{"answer_correct": true}` for trivia, `{"predicted_score": 3}` for a prediction. Mirrors the Amplitude/Mixpanel "properties bag" pattern: new widget types or experiment variants can attach arbitrary metadata without a schema migration. Only populated on `interaction` events currently; `{}` otherwise. |

---

## `user_points`

One row per user — a rolled-up leaderboard snapshot.

| Column | Type | Business meaning |
|---|---|---|
| `user_id` | `PK / FK -> users` | |
| `total_points` | `INTEGER` | Sum of `points_earned` across all their events. |
| `current_rank` | `INTEGER` | Standard competition rank (`RANK()` semantics — ties share a rank, next rank skips, e.g. 1,2,2,4). |
| `last_updated` | `TIMESTAMPTZ` | In this synthetic dataset, always the simulation end time (computed once, in batch). In production this would be maintained incrementally — see README "How I'd productionize this." |

---

## `badges`

One row per achievement a user has unlocked. Append-only log (a user can earn the same badge concept once; no uniqueness constraint is enforced since re-earning isn't modeled).

| Column | Type | Business meaning |
|---|---|---|
| `badge_id` | `SERIAL PK` | |
| `user_id` | `FK -> users` | |
| `badge_name` | `VARCHAR(100)` | e.g. "First Steps", "Century Club", "Top 100 Fan", "Super Fan" — threshold-based, see `generate_badges()`. |
| `earned_date` | `TIMESTAMPTZ` | When the threshold was crossed. In the synthetic generator this is a random date in the simulation window (an approximation — the real event sequence isn't replayed to find the exact crossing moment). |

---

## `experiments`

One row per A/B test definition.

| Column | Type | Business meaning |
|---|---|---|
| `experiment_id` | `SERIAL PK` | |
| `experiment_name` | `VARCHAR(150)` | Human-readable name. |
| `hypothesis` | `TEXT` | The specific, falsifiable claim being tested — e.g. "A personalized feed increases Day-7 retention vs chronological." Every experiment in this dataset states one. |
| `metric` | `VARCHAR(100)` | The primary metric the experiment is judged on (e.g. `day_7_retention`). Guardrail metrics are tracked separately in the experimentation analysis layer (Phase 4), not in this table. |
| `start_date` / `end_date` | `TIMESTAMPTZ` | Experiment window. `end_date` is `NULL` for a still-running experiment. |
| `status` | `planned \| running \| completed \| shipped \| rolled_back` | Lifecycle state. |

---

## `experiment_assignments`

One row per (user, experiment) pair — which variant a user was bucketed into.

| Column | Type | Business meaning |
|---|---|---|
| `user_id`, `experiment_id` | `Composite PK / FK`s | A user is assigned to each experiment at most once. |
| `variant` | `VARCHAR(30)` | e.g. `control`/`treatment`, or `morning`/`evening`/`ml_optimized` for a multi-arm test. |
| `assigned_at` | `TIMESTAMPTZ` | When the assignment was made. |

**Assignment is deterministic and hash-based**, not a fresh random draw per request: `variant = f(md5(user_id + experiment_id))`. This is what real experimentation platforms (GrowthBook, LaunchDarkly, in-house systems) do — it guarantees a user always sees the same variant across repeat visits without needing a sticky session cookie, and it's exactly reproducible. A naive `random.choice()` per pageview would flicker a user between control and treatment on every load, contaminating the experiment.

---

## Entity Relationship Summary

```
users ──< sessions ──< widget_events >── widgets
  │           
  ├──< user_points (1:1)
  ├──< badges
  └──< experiment_assignments >── experiments
```

## Design Notes

- **Why `widgets`/`widget_events` instead of generic `content`/`events` naming?** This product models LiveLike-style engagement widgets (polls, trivia, predictions, leaderboards) specifically, not a generic video/article feed. Keeping the domain-specific names is more defensible in an interview ("I modeled the actual product LiveLike builds") than forcing a generic Amplitude schema onto a different product shape.
- **`properties JSONB` on `widget_events`** is the one concession to the generic event-schema pattern — it gives the fact table room to grow (new widget types, new experiment-specific metadata) without a migration, while keeping `event_type`/`points_earned` as first-class typed columns since they're queried in every funnel/retention query and don't need JSONB's flexibility.
- **`user_segment` and `acquisition_channel` are correlated by design**, not independent random draws — see `CHANNEL_QUALITY_MULTIPLIER`. This is what makes "engagement rate by acquisition channel" (a `queries.sql`/dashboard breakdown) an interesting, non-trivial result instead of flat noise.
