# Fan Engagement Platform — Analytics Project

An end-to-end analytics project simulating a sports/media **fan engagement & gamification platform** (polls, trivia, predictions, leaderboards — in the spirit of LiveLike's widget products). It models, generates, queries, and visualizes engagement data using a real cloud Postgres database and a self-hosted BI dashboard.

The goal: demonstrate the full analytics workflow a Data Analyst would own — schema design → realistic synthetic data → a clean, commented SQL analysis layer → a polished Metabase dashboard — not just a notebook with a CSV.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | PostgreSQL (hosted on Supabase, free tier) |
| Data generation | Python (`faker`, `numpy`, `psycopg2`) |
| Analysis | SQL (CTEs, window functions, subqueries, conditional aggregation) |
| Dashboards | Metabase (self-hosted via Docker) |

---

## Architecture

![Architecture Diagram](architecture.png)

Synthetic data is generated in Python and batch-loaded into Supabase Postgres. `queries.sql` contains the analysis layer that runs against Postgres. Metabase connects to the same database and renders the dashboard.

---

## Dataset at a Glance

Generated with a deliberately realistic shape rather than uniform random data:

- **3,000 users** across 15 countries and 3 device types
- **~109,000 sessions** over a 6-month window
- **~476,000 widget events** (impressions, interactions, completions)
- **Power-law engagement**: the top 20% of users drive ~78% of all sessions — modeled with a Pareto-weighted distribution, not `random.randint()`
- **Front-loaded signups**: a launch spike that tapers over time, so retention cohorts have realistic maturity differences

---

## Schema

Seven tables: a central `widget_events` fact table surrounded by dimension and rollup tables.

```
users (user_id PK, signup_date, country, device_type)
  │
  ├──< sessions (session_id PK, user_id FK, app_open_time, app_close_time, platform)
  │       │
  │       └──< widget_events (event_id PK, widget_id FK, user_id FK, session_id FK,
  │                            event_type, event_timestamp, points_earned)
  │                  │
widgets (widget_id PK, widget_type, name, sport, launch_date) >──┘
  │
user_points (user_id PK/FK, total_points, current_rank, last_updated)
  │
badges (badge_id PK, user_id FK, badge_name, earned_date)
```

- `widget_type` ∈ {poll, trivia, prediction, leaderboard}
- `event_type` ∈ {impression, interaction, completion}
- All foreign keys enforced with `ON DELETE CASCADE`; indexes on FK columns and frequently-filtered columns (`event_timestamp`, `event_type`, `user_id`).

---

## How to Run

### 1. Set up the database

Create a free Postgres database on [Supabase](https://supabase.com), then store the connection string in a `.env` file:

```
DATABASE_URL=postgresql://postgres.xxxxx:yourpassword@aws-region.pooler.supabase.com:5432/postgres
```

### 2. Install dependencies

```bash
pip install psycopg2-binary python-dotenv faker numpy
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
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

Open `http://localhost:3000`, connect Metabase to your Supabase database (PostgreSQL, SSL mode `require`), and build the dashboard from the saved questions.

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

The Metabase dashboard is organized into two tabs:

**Tab 1 — Overview** (the at-a-glance health metrics):
1. DAU / WAU / MAU trend line
2. Widget engagement rate by type (bar)
3. Engagement funnel (funnel chart)
4. Engagement value by user tier (power-law bar)

**Tab 2 — Leaderboard & Retention** (the detail tables):
5. Retention cohort heatmap (conditional-formatted table)
6. Top 10 leaderboard (live table)

*(Screenshots below.)*

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
| `generate_data.py` | Synthetic data generation and batch loading |
| `verify_data.py` | Data validation (row counts, orphan checks, distributions) |
| `queries.sql` | The 8-query analysis layer, fully commented |
| `architecture.png` | Data flow diagram |
| `README.md` | This file |
