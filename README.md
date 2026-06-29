# Pulse — Fan Engagement Analytics Platform

An end-to-end **product analytics platform** simulating a sports/media fan engagement & gamification product (polls, trivia, predictions, leaderboards — in the spirit of LiveLike's widget products). Schema design → realistic synthetic data at scale → a documented metrics layer → A/B experimentation → a hybrid recommendation engine → an interactive dashboard → a deployed, cinematic showcase site. The kind of full-stack analytics + ML system a data/product team at a consumer product company actually builds and lives in, not a one-off notebook.

**Live:**
- 🌐 Showcase site: **[fan-engagement-platform-teal.vercel.app](https://fan-engagement-platform-teal.vercel.app)**
- 🔌 API (live recommendation demo): **[fan-engagement-platform-api.onrender.com](https://fan-engagement-platform-api.onrender.com)**

![Hero](docs/screenshots/hero.png)

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | PostgreSQL (hosted on Supabase, free tier) |
| Data generation | Python (`faker`, `numpy`, `psycopg2`) |
| Metrics layer | Python (`pandas`) wrappers over parameterized `.sql` files |
| Experimentation | Python — two-sample tests, CUPED variance reduction, sequential testing |
| Recommendations | `implicit` (ALS collaborative filtering), `scikit-learn` (content similarity), `LightGBM` (hybrid ranker) |
| Dashboard | Streamlit + Plotly (interactive, in-repo — not an external BI tool) |
| Showcase site | Next.js (App Router) + TypeScript + Tailwind + GSAP/Lenis scroll choreography |
| API | FastAPI, deployed on Render |
| Site hosting | Vercel |

---

## Architecture

![Architecture Diagram](architecture.png)

Synthetic data is generated in Python and batch-loaded into Supabase Postgres. The `metrics/` module (Phase 2) wraps every business metric in a documented `.sql` file + Python function returning a pandas DataFrame. `dashboard/app.py` (Phase 3) pulls exclusively from `metrics/` — no metric is computed inline in the dashboard. `experimentation/` (Phase 4) runs the same statistical engine against three pre-seeded A/B tests. `recommendations/` (Phase 5) trains a hybrid CF + content recommender and serves it from both the dashboard and a standalone FastAPI service. `site/` (Phase 6) is a separate Next.js showcase deployed to Vercel, reading a precomputed JSON snapshot (`snapshot/build_snapshot.py`) for instant loads, with one genuinely live piece — a recommendation demo calling the FastAPI service on Render.

```
Supabase Postgres
   │
   ├─ metrics/ ───────────────► dashboard/app.py (Streamlit, 7 tabs)
   ├─ experimentation/ ───────► dashboard Experiments tab
   ├─ recommendations/ ───────► dashboard Recommendations tab
   │        │
   │        └─ train_and_save.py → recommendations/model_state.pkl
   │                                       │
   │                                       ▼
   │                            api/main.py (FastAPI, deployed on Render)
   │                                       ▲
   │                                       │ live fetch
   └─ snapshot/build_snapshot.py ─► site/data/snapshot.json ─► site/ (Next.js, deployed on Vercel)
```

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
python run_schema.py        # creates the tables + indexes
python generate_data.py     # generates and loads ~2M rows
python verify_data.py       # sanity checks: row counts, orphaned FKs, distributions
```

`generate_data.py` is idempotent (it truncates and reseeds on every run) and inserts in chunks with retry/reconnect logic, since free-tier pooled connections can drop on long-running batch operations.

### 4. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501`. Seven tabs, every chart pulling from the `metrics/`, `experimentation/`, and `recommendations/` layers — nothing computed inline in the dashboard.

### 5. Train the recommender (for the API)

```bash
python -m recommendations.train_and_save
```

Trains the ALS + LightGBM hybrid model and saves `recommendations/model_state.pkl`. Re-run whenever the underlying data changes; the API loads this file at boot rather than training live (see [Productionizing the recommender](#productionizing-the-recommender) below for why).

### 6. Run the API locally

```bash
uvicorn api.main:app --reload
```

### 7. Run the showcase site locally

```bash
cd site
npm install
npm run build && npm run start   # or `npm run dev` for hot-reload
```

Set `NEXT_PUBLIC_API_URL` in `site/.env.local` to point at your local or deployed API.

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

## Experimentation

Three pre-seeded A/B tests, each assigned at signup via deterministic hashing, analyzed with one shared statistical engine (`experimentation/`):

- **Personalized feed vs. chronological** — primary metric (bounded Day-7 retention) lift of +100%, guardrail (avg. session duration) clean. **Shipped.**
- **Push notification timing** — includes a sequential-peeking demonstration: stopping at 75% of the data already looks significant (p < 0.05 on the naive threshold), but the properly alpha-spending-adjusted threshold at that look is stricter — waiting for the full sample is what actually justifies shipping.
- **Onboarding flow change** — full two-sample test, CI, and guardrail check.

Every result includes CUPED variance reduction, a per-segment breakdown, and an explicit ship/no-ship decision combining statistical and practical significance — not p-value alone.

![Experiments](docs/screenshots/experiments.png)

---

## Recommendations

A hybrid recommender (`recommendations/`) combining:

- **Collaborative filtering** — ALS on the implicit-feedback interaction matrix (impressions/interactions/completions weighted by strength).
- **Content-based similarity** — cosine similarity over widget-type and sport features, the cold-start fallback for users or widgets with no history.
- **Hybrid ranker** — a LightGBM classifier combining the CF score, content similarity, segment-level content-type affinity, recency, and time-of-day match into a single ranking score.

Evaluated on a **temporal** (not random) train/test split, so the model never sees a user's future interactions during training. Headline finding: pure collaborative filtering goes completely blind on cold-start users (0% Recall@10), while the hybrid model degrades gracefully instead — the whole point of comparing methods rather than shipping CF alone.

![Recommendations](docs/screenshots/recommendations.png)

### Productionizing the recommender

Training (load the full interaction history → ALS → build LightGBM training examples) needs the entire event-level dataset and a sparse interaction matrix in memory at once — `recommendations/train_and_save.py` runs this once and pickles only what `get_recommendation()` actually needs to serve a request (a handful of small lookup dicts and the trained models, not the raw data). The deployed API loads that ~11MB pickle at boot instead of retraining on every cold start — this is also what makes the free-tier Render deployment work at all inside its 512MB memory limit.

---

## Showcase Site (Phase 6)

A scroll-driven cinematic homepage (`site/`, Next.js + GSAP + Lenis) told in seven movements, sharing one persistent SVG point-field across all of them so nothing hard-cuts between sections:

1. **Hook** — the field of fans multiplies and settles into a grid.
2. **Retention** — the grid resolves into the real cohort heatmap (censored cells fade to neutral, not a false 0%).
3. **Funnel** — points physically fall into a narrowing funnel mouth, the ones that don't make it colliding and dropping away — the real signup→engagement leak, dramatized.
4. **Experiments** — a guardrail dip that looks alarming, corrected by the real numbers; a peeking-problem chart shown live.
5. **Recommendations** — the surviving cohort becomes a node-link graph; a cold-start node gets threaded in via content similarity.
6. **Scale & impact** — the graph condenses to a point while real headline KPIs cycle through, then unfurls back into the same pulse line the page opened with.
7. **Dashboard emergence** — that pulse line shrinks into the real dashboard's logo mark, scroll-jacking permanently releases, and the actual interactive dashboard (same routes as the Streamlit app, reimplemented natively) takes over.

Below the fold: the live recommendation demo, calling the deployed FastAPI service directly from the browser.

![Dashboard](docs/screenshots/dashboard-overview.png)
![Retention](docs/screenshots/retention.png)
![Funnels](docs/screenshots/funnels.png)

---

## What the Data Reveals (Business Insights)

Written for a product/business audience — what each panel actually tells you.

**1. Engagement is widget-design-driven, not platform- or geography-driven.**
Polls convert impressions to interactions at 45% vs. just 20% for leaderboards — a 2.25x gap. Meanwhile, engagement rate is essentially flat across all 15 countries (29.8%–31.0%) and all device types (30.2%–30.4%). Takeaway: invest in *which widget formats to build* (more polls, fewer passive leaderboards), not in region- or platform-specific optimization.

**2. The funnel's real drop-off is mid-funnel, and it varies by widget type.**
Platform-wide, only 30% of impressions become interactions, but 67% of interactions complete. Leaderboards and polls convert almost everyone who starts (~90% completion), while trivia and prediction widgets — which require actual effort — lose ~45% mid-funnel. Takeaway: UX improvements should target trivia/prediction *completion*, not top-of-funnel reach.

**3. Engagement value is extremely concentrated — a classic power-law.**
The top third of users by points ("power users") drive **93% of all points and completions**; the bottom third contribute under 1%. Takeaway: retention spend on casual one-time users is likely wasted — the real lever is converting "regular" users into power users, where nearly all engagement value lives.

**4. Retention stabilizes rather than collapsing.**
After the expected week-0-to-week-1 settling, weekly retention holds steady in the ~40–55% band for mature cohorts rather than decaying to zero — a healthy sign that the gamification loop creates a returning habit, not just one-time curiosity.

**5. Personalization is worth shipping, even when the guardrail looks scary at first glance.**
The feed-personalization experiment's guardrail (session duration) dipped initially — noise, not a real effect (p = 0.80) — while the primary metric (Day-7 retention) nearly doubled. Takeaway: a single alarming-looking chart isn't a verdict; check statistical significance before reacting to it.

**6. Cold-start users need a different recommendation strategy entirely, not a worse version of the same one.**
Pure CF has literally nothing to say about a user with no history (0% Recall@10) — the hybrid model's graceful degradation into content-based fallback is what makes recommendations viable for new users at all.

---

## Design Notes & Engineering Decisions

A few choices worth calling out, and bugs caught and fixed along the way:

- **Validated the data, didn't just trust it.** `verify_data.py` confirms zero orphaned foreign keys and that the generated distributions actually match the intended design (the 78%-from-top-20% power-law was a target I calibrated to, then verified). Three real bugs were caught and fixed during development: a `psycopg2 execute_values` + `RETURNING` pagination bug that was silently truncating inserts, a distribution-clipping bug that piled overflow values onto the final day (producing a fake DAU spike), and a cohort-window bug that anchored retention weeks to the calendar week instead of each user's own signup date.

- **Retention is measured relative to each user's signup date**, not a fixed calendar week — so "week 0" means a user's own first 7 days, regardless of which weekday they joined. This avoids systematically understating week-0 retention.

- **Censored cohorts are shown as blank, not zero.** Recent cohorts that haven't existed long enough to measure week N show `NULL` (blank cells) rather than a misleading `0%`.

- **Caught a Supabase free-tier query timeout the hard way.** The recommender's full 3-table join (`widget_events` ⋈ `widgets` ⋈ `users`, ~2M rows) started outright failing `statement_timeout` on the free-tier pooler — every index needed was already in place, it was simply more join than the free compute tier could finish in one statement. Fixed by splitting the query into monthly WHERE-bounded statements instead of one giant join, trading round trips for statements that reliably finish.

- **Caught a hydration mismatch the hard way too.** `toLocaleString()` without an explicit locale rendered different digit grouping on the Node SSR process vs. the browser (`20,62,633` vs `2,062,633`), silently corrupting React's hydration and breaking the cinematic site's scroll-pin measurements downstream. Fixed by pinning `"en-US"` on every call site.

### How I'd productionize this further

This project batch-computes `user_points` from `widget_events` in `generate_data.py`, since the data is synthetic and generated once. In production, `user_points` would be maintained incrementally — via a Postgres trigger on `widget_events` inserts, or a scheduled job recomputing rankings in near-real-time. A trigger keeps the leaderboard always current but adds write-path latency; a scheduled batch job is simpler and sufficient when a few minutes of leaderboard staleness is acceptable (the more common real-world tradeoff). At scale, I'd also partition `widget_events` by month once it grows past a few million rows, since most queries filter by `event_timestamp`. The recommender would similarly move from "retrain via a manual script" to a scheduled retraining job (e.g. nightly), with the API hot-swapping in the new model state rather than requiring a redeploy.

---

## Repository Contents

| Path | Purpose |
|---|---|
| `schema.sql` | Table definitions, constraints, indexes |
| `data_dictionary.md` | Full table/column reference with business definitions |
| `generate_data.py` | Synthetic data generation and batch loading |
| `verify_data.py` | Data validation (row counts, orphan checks, distributions) |
| `queries.sql` | The 8-query analysis layer, fully commented |
| `metrics/` | Parameterized `.sql` files + Python wrappers — the metrics layer the dashboard reads from |
| `experimentation/` | Shared A/B testing statistical engine (two-sample tests, CUPED, sequential testing) |
| `recommendations/` | Hybrid CF + content recommender: training, evaluation, and the FastAPI router that serves it |
| `dashboard/app.py` | Streamlit executive dashboard (7 tabs) |
| `api/` | FastAPI app deployed on Render — mounts the recommendation router + a `/snapshot` endpoint |
| `snapshot/build_snapshot.py` | Precomputes the JSON snapshot the showcase site bakes in at build time |
| `site/` | The Next.js cinematic showcase site, deployed on Vercel |
| `DEPLOYMENT_PLAN.md` | Render + Vercel deployment steps, env vars, and known gaps |
| `requirements.txt` | Pinned Python dependencies |
| `architecture.png` | Data flow diagram |
| `docs/screenshots/` | Screenshots used in this README |
| `README.md` | This file |
