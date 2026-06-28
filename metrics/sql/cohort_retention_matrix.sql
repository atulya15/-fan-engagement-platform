-- ================================================================
-- Cohort retention matrix: % of each signup-week cohort active in
-- week N after their OWN signup (weeks 0-11)
-- ================================================================
-- Business question: the single most-asked-about product metric.
-- If 100 users sign up in a given week, how many are still active
-- 1/2/3+ weeks later? Read down a column to see whether retention is
-- improving release-over-release; read across a row to see how a
-- single cohort decays (or stabilizes) over time.
--
-- Two things this query gets deliberately right:
--   1. week_number is days-since-the-user's-OWN-signup / 7, not a
--      calendar-week bucket -- bucketing by calendar week would make
--      week 0 artificially short for a user who signs up mid-week,
--      understating week-0 retention for no real reason.
--   2. CENSORED cells are NULL, not 0%. A cohort that signed up two
--      weeks ago cannot have a "week 5 retention" yet -- that's not
--      the same as 0% of them returning in week 5. Conflating
--      "hasn't happened yet" with "happened and failed" is the
--      second most common retention bug after the censoring bug in
--      day_n_retention.sql. We build the full cohort x week grid
--      explicitly, then NULL out any cell where the cohort isn't old
--      enough yet, so a dashboard renders blank cells instead of a
--      misleading 0%.
-- ================================================================

WITH user_cohort AS (
    SELECT
        user_id,
        signup_date,
        DATE_TRUNC('week', signup_date)::date AS cohort_week
    FROM users
),

cohort_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM user_cohort
    GROUP BY cohort_week
),

user_activity_weeks AS (
    SELECT DISTINCT
        s.user_id,
        uc.cohort_week,
        FLOOR(EXTRACT(EPOCH FROM (s.app_open_time - uc.signup_date)) / (7 * 86400))::int AS week_number
    FROM sessions s
    JOIN user_cohort uc ON s.user_id = uc.user_id
    WHERE s.app_open_time >= uc.signup_date
),

retention_counts AS (
    SELECT cohort_week, week_number, COUNT(DISTINCT user_id) AS active_users
    FROM user_activity_weeks
    WHERE week_number BETWEEN 0 AND 11
    GROUP BY cohort_week, week_number
),

-- Full cross-product grid: every cohort x every week 0-11, so missing
-- combinations are visible as explicit rows (then classified below as
-- either "0% retention" or "censored / not old enough yet").
grid AS (
    SELECT cs.cohort_week, w.week_number, cs.cohort_size
    FROM cohort_sizes cs
    CROSS JOIN (SELECT generate_series(0, 11) AS week_number) w
)

SELECT
    g.cohort_week,
    g.cohort_size,
    g.week_number,
    rc.active_users,
    CASE
        -- Censored: this cohort hasn't existed long enough to have
        -- reached week_number yet (need a full week_number+1 weeks
        -- elapsed since the cohort started).
        WHEN g.cohort_week + ((g.week_number + 1) * 7 || ' days')::interval
             > (SELECT MAX(app_open_time) FROM sessions)
        THEN NULL
        ELSE ROUND(100.0 * COALESCE(rc.active_users, 0) / g.cohort_size, 1)
    END AS retention_pct
FROM grid g
LEFT JOIN retention_counts rc
    ON rc.cohort_week = g.cohort_week AND rc.week_number = g.week_number
ORDER BY g.cohort_week, g.week_number;
