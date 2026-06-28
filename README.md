# Fan Engagement Platform — Product Analytics Platform

An end-to-end **product analytics platform** simulating a sports/media fan engagement & gamification product (polls, trivia, predictions, leaderboards — in the spirit of LiveLike's widget products). Schema design → realistic synthetic data at scale → a documented metrics layer → an interactive executive dashboard — the kind of internal tool a data team at a consumer product company actually builds and lives in, not a one-off notebook.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | PostgreSQL (hosted on Supabase, free tier) |
| Data generation | Python (`faker`, `numpy`, `psycopg2`) |
| Metrics layer | Python (`pandas`) wrappers over parameterized `.sql` files |
| Dashboard | Streamlit + Plotly (interactive, in-repo — not an external BI tool) |

---

## Architecture

![Architecture Diagram](architecture.png)

Synthetic data is generated in Python and batch-loaded into Supabase Postgres. The `metrics/` module (Phase 2) wraps every business metric in a documented `.sql` file + Python function returning a pandas DataFrame. `dashboard/app.py` (Phase 3) pulls exclusively from `metrics/` — no metric is computed inline in the dashboard, so every chart and any future consumer of `metrics/` always agree on the number. `queries.sql` remains as a standalone, heavily-commented SQL reference layer (8 queries) separate from the parameterized metrics module.

---

## Dataset at a Glance

Generated with a deliberately realistic shape rather than uniform random data:

- **10,000 users** across 15 countries, 3 device types, and 5 acquisition channels
- **~320,000 sessions** over a 12-month window
- **~2.0M widget events** (impressions, interactions, completions)
- **Power-law engagement**: the top 20% of users drive ~78% of all sessions — modeled with a Pareto-weighted distribution, not `random.randint()`
- **Channel-quality-weighted engagement**: organic/referral users engage ~15% above the power-law baseline; paid_social/influencer users ~35–45% below it — acquisition channel isn't just a label, it actually drives different behavior in the data
- **Front-loaded signups**: a launch spike that tapers over time, so retention cohorts have realistic maturity differences
- **3 pre-seeded A/B experiments** with deterministic hash-based variant assignment across all 10,000 users

See [`data_dictionary.md`](data_dictionary.md) for the full table/column reference.

---

## Schema

Nine tables: a central `widget_events` fact table surrounded by dimension, rollup, and experimentation tables. Full column-level reference in [`data_dictionary.md`](data_dictionary.md).

```
users (user_id PK, signup_date, country, device_type, user_segment, acquisition_channel)
  │
  ├──< sessions (session_id PK, user_id FK, app_open_time, app_close_time, platform)
  │       │
  │       └──< widget_events (event_id PK, widget_id FK, user_id FK, session_id FK,
  │                            event_type, event_timestamp, points_earned, properties JSONB)
  │                  │
  ├── widgets (widget_id PK, widget_type, name, sport, launch_date) >──┘
  │
  ├── user_points (user_id PK/FK, total_points, current_rank, last_updated)
  ├── badges (badge_id PK, user_id FK, badge_name, earned_date)
  └──< experiment_assignments (user_id FK, experiment_id FK, variant, assigned_at) >── experiments
                                                                       (experiment_id PK, experiment_name,
                                                                        hypothesis, metric, start_date,
                                                                        end_date, status)
```

- `widget_type` ∈ {poll, trivia, prediction, leaderboard}
- `event_type` ∈ {impression, interaction, completion}
- `user_segment` ∈ {free, premium, churned} — derived post-hoc from actual session/points behavior, not assigned at signup
- `acquisition_channel` ∈ {organic, paid_social, referral, influencer, app_store_search}
- All foreign keys enforced with `ON DELETE CASCADE`; indexes on FK columns and frequently-filtered columns (`event_timestamp`, `event_type`, `user_id`, `user_segment`, `acquisition_channel`).

---

## How to Run

### 1. Set up the database

Create a free Postgres database on [Supabase](https://supabase.com), then store the connection string in a `.env` file:

```
DATABASE_URL=postgresql://postgres.xxxxx:yourpassword@aws-region.pooler.supabase.com:5432/postgres
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Build the schema and generate data

```bash
python run_schema.py        # creates the 7 tables + indexes
python generate_data.py     # generates and loads ~476K rows
python verify_data.py       # sanity checks: row counts, orphaned FKs, distributions
```

`generate_data.py` is idempotent (it truncates and reseeds on every run) and inserts in chunks with retry/reconnect logic, since free-tier pooled connections can drop on long-running batch operations.

### 4. Run the analysis

Open `queries.sql` and run any query against your database (via the Supabase SQL Editor or `psql`).

### 5. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501`. Seven tabs: Overview, Retention, Funnels, Content, Growth, Experiments, Recommendations (the last two are placeholders until Phases 4-5 land). Every chart pulls from the `metrics/` layer — nothing is computed inline in the dashboard.

---

## The SQL Analysis Layer

`queries.sql` contains **8 queries** — the 6 core deliverables plus 2 stretch analyses. Each is commented to explain intent, not just mechanics.

| # | Query | Key technique |
|---|---|---|
| 1 | DAU / WAU / MAU | CTE + correlated subqueries, `COUNT(DISTINCT)` |
| 2 | Widget engagement rate by type | `FILTER` conditional aggregation, `NULLIF` |
| 3 | Gamification funnel (impression → interaction → completion) | `LAG`, `RANK` window functions, `UNION ALL` unpivot |
| 4 | Retention cohorts (% active in week N after signup) | Multi-stage CTEs, relative-date math, manual pivot |
| 5 | Top 10 leaderboard | `RANK() OVER (ORDER BY total_points DESC)` |
| 6 | Rolling 7-day active users | `AVG() OVER (... RANGE BETWEEN ...)` window frame |
| 7 | Power user segmentation *(stretch)* | `NTILE(3)`, `SUM() OVER ()` |
| 8 | Engagement rate by country & device *(stretch)* | `UNION ALL` of two breakdowns |

---

## Dashboard

A Streamlit app (`dashboard/app.py`), not an external BI tool — interactive, in-repo, and pulling exclusively from the `metrics/` layer. Seven tabs:

1. **Overview** — DAU/WAU/MAU trend, stickiness (DAU/MAU), session duration/frequency percentiles, one-line insight under each chart.
2. **Retention** — cohort retention heatmap (censored cells shown blank, not a misleading 0%), Day-N bounded vs. unbounded retention, rolling 28-day retention, segment breakdowns by acquisition channel and device.
3. **Funnels** — signup → first view → first engagement → repeat engagement → premium conversion (funnel chart), plus a per-channel breakdown.
4. **Content** — engagement rate by widget type × sport category, engagement-depth distribution, top/bottom widget performance ranking.
5. **Growth** — new/returning/resurrected users (stacked area), Quick Ratio over time.
6. **Experiments** — placeholder pending Phase 4.
7. **Recommendations** — placeholder pending Phase 5.

*(Screenshots from the prior Metabase-based version below are stale and will be replaced once the Streamlit dashboard is deployed in Phase 6.)*

![Overview Tab](dashboard-overview.png)

![Leaderboard & Retention Tab](dashboard-retention.png)

---

## What the Dashboard Reveals (Business Insights)

Written for a product/business audience — what each panel actually tells you.

**1. Engagement is widget-design-driven, not platform- or geography-driven.**
Polls convert impressions to interactions at 45% vs. just 20% for leaderboards — a 2.25x gap. Meanwhile, engagement rate is essentially flat across all 15 countries (29.8%–31.0%) and all device types (30.2%–30.4%). Takeaway: invest in *which widget formats to build* (more polls, fewer passive leaderboards), not in region- or platform-specific optimization.

**2. The funnel's real drop-off is mid-funnel, and it varies by widget type.**
Platform-wide, only 30% of impressions become interactions, but 67% of interactions complete. Leaderboards and polls convert almost everyone who starts (~90% completion), while trivia and prediction widgets — which require actual effort — lose ~45% mid-funnel. Takeaway: UX improvements should target trivia/prediction *completion*, not top-of-funnel reach.

**3. Engagement value is extremely concentrated — a classic power-law.**
The top third of users by points ("power users") drive **93% of all points and completions**; the bottom third contribute under 1%. Takeaway: retention spend on casual one-time users is likely wasted — the real lever is converting "regular" users into power users, where nearly all engagement value lives.

**4. Retention stabilizes rather than collapsing.**
After the expected week-0-to-week-1 settling, weekly retention holds steady in the ~40–55% band for mature cohorts rather than decaying to zero — a healthy sign that the gamification loop creates a returning habit, not just one-time curiosity.

---

## Design Notes & Engineering Decisions

A few choices worth calling out, and bugs caught and fixed along the way:

- **Validated the data, didn't just trust it.** `verify_data.py` confirms zero orphaned foreign keys and that the generated distributions actually match the intended design (the 78%-from-top-20% power-law was a target I calibrated to, then verified). Three real bugs were caught and fixed during development: a `psycopg2 execute_values` + `RETURNING` pagination bug that was silently truncating inserts, a distribution-clipping bug that piled overflow values onto the final day (producing a fake DAU spike), and a cohort-window bug that anchored retention weeks to the calendar week instead of each user's own signup date.

- **Retention is measured relative to each user's signup date**, not a fixed calendar week — so "week 0" means a user's own first 7 days, regardless of which weekday they joined. This avoids systematically understating week-0 retention.

- **Censored cohorts are shown as blank, not zero.** Recent cohorts that haven't existed long enough to measure week N show `NULL` (blank cells) rather than a misleading `0%`.

### How I'd productionize this

This project batch-computes `user_points` from `widget_events` in `generate_data.py`, since the data is synthetic and generated once. In production, `user_points` would be maintained incrementally — via a Postgres trigger on `widget_events` inserts, or a scheduled job recomputing rankings in near-real-time. A trigger keeps the leaderboard always current but adds write-path latency; a scheduled batch job is simpler and sufficient when a few minutes of leaderboard staleness is acceptable (the more common real-world tradeoff). At scale, I'd also partition `widget_events` by month once it grows past a few million rows, since most queries filter by `event_timestamp`.

---

## Repository Contents

| File | Purpose |
|---|---|
| `schema.sql` | Table definitions, constraints, indexes |
| `data_dictionary.md` | Full table/column reference with business definitions |
| `generate_data.py` | Synthetic data generation and batch loading |
| `verify_data.py` | Data validation (row counts, orphan checks, distributions) |
| `queries.sql` | The 8-query analysis layer, fully commented |
| `metrics/` | Parameterized `.sql` files + Python wrappers — the metrics layer the dashboard reads from |
| `dashboard/app.py` | Streamlit executive dashboard (7 tabs) |
| `requirements.txt` | Pinned dependencies |
| `architecture.png` | Data flow diagram |
| `README.md` | This file |
