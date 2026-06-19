-- ================================================================
-- FAN ENGAGEMENT PLATFORM — SQL ANALYSIS LAYER
-- ================================================================
-- Each query below answers a specific product/business question.
-- Comments explain intent, not just mechanics.
-- ================================================================


-- ================================================================
-- 1. DAU / WAU / MAU
-- ================================================================
-- Business question: How many unique users engage with the platform
-- daily, weekly, and monthly? This is the foundational health metric
-- for any consumer product — used to track growth, spot decline, and
-- benchmark against engagement targets.
--
-- Technique: three separate aggregations unioned together, each using
-- COUNT(DISTINCT user_id) over a different time grain. We use a CTE
-- to derive "active day" once, then reuse it for all three rollups.
-- ================================================================

WITH daily_activity AS (
    SELECT
        DATE(app_open_time) AS activity_date,
        user_id
    FROM sessions
    GROUP BY DATE(app_open_time), user_id
)

SELECT
    activity_date,
    COUNT(DISTINCT user_id) AS dau,

    -- WAU: distinct users active at any point in the trailing 7 days
    -- (including today), computed per day via a correlated subquery.
    (
        SELECT COUNT(DISTINCT user_id)
        FROM daily_activity d2
        WHERE d2.activity_date BETWEEN da.activity_date - INTERVAL '6 days'
                                    AND da.activity_date
    ) AS wau,

    -- MAU: distinct users active at any point in the trailing 30 days
    (
        SELECT COUNT(DISTINCT user_id)
        FROM daily_activity d3
        WHERE d3.activity_date BETWEEN da.activity_date - INTERVAL '29 days'
                                    AND da.activity_date
    ) AS mau

FROM daily_activity da
GROUP BY activity_date
ORDER BY activity_date;

-- ================================================================
-- 2. WIDGET-LEVEL ENGAGEMENT RATE
-- ================================================================
-- Business question: Of the four widget types (poll, trivia,
-- prediction, leaderboard), which ones do fans actually engage with
-- once they see them? This tells product/content teams where to
-- invest — e.g. "polls convert 2x better than leaderboards, build
-- more polls."
--
-- Technique: conditional aggregation using FILTER (a cleaner,
-- more readable alternative to CASE WHEN inside COUNT/SUM), plus
-- a derived rate computed with NULLIF to safely avoid divide-by-zero.
-- ================================================================

SELECT
    w.widget_type,

    COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
    COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
    COUNT(*) FILTER (WHERE we.event_type = 'completion')  AS completions,

    -- Engagement rate: what % of impressions turned into an interaction
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE we.event_type = 'interaction')
        / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'impression'), 0),
        1
    ) AS engagement_rate_pct,

    -- Completion rate: of those who interacted, what % finished
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE we.event_type = 'completion')
        / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'interaction'), 0),
        1
    ) AS completion_rate_pct

FROM widget_events we
JOIN widgets w ON we.widget_id = w.widget_id
GROUP BY w.widget_type
ORDER BY engagement_rate_pct DESC;

-- ================================================================
-- 3. GAMIFICATION FUNNEL: impression -> interaction -> completion
-- ================================================================
-- Business question: Across the whole platform, how much drop-off
-- happens at each stage of the funnel, and which widget_type has the
-- steepest fall-off between stages? This is the headline funnel view
-- a product manager would want on a dashboard.
--
-- Technique:
--   - LAG() window function to pull the PREVIOUS stage's count into
--     the same row, so we can compute stage-over-stage drop-off
--     without a self-join.
--   - RANK() window function to rank widget_types by their overall
--     completion rate. RANK() is computed once per widget_type (4
--     rows) in its own CTE, then joined onto the long/unpivoted
--     funnel data (12 rows) — computing it directly on the long
--     data would rank stages, not widget_types, which is wrong.
-- ================================================================

WITH funnel_by_widget AS (
    SELECT
        w.widget_type,
        COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
        COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
        COUNT(*) FILTER (WHERE we.event_type = 'completion')  AS completions
    FROM widget_events we
    JOIN widgets w ON we.widget_id = w.widget_id
    GROUP BY w.widget_type
),

-- Rank widget_types by overall completion rate (completions / impressions).
-- One row per widget_type -- this is the correct grain for RANK() here.
widget_ranks AS (
    SELECT
        widget_type,
        ROUND(100.0 * completions / NULLIF(impressions, 0), 1) AS overall_completion_rate_pct,
        RANK() OVER (
            ORDER BY 100.0 * completions / NULLIF(impressions, 0) DESC
        ) AS overall_completion_rank
    FROM funnel_by_widget
),

-- Unpivot into one row per (widget_type, funnel_stage) so LAG() can
-- walk stage-to-stage within each widget_type's funnel.
funnel_long AS (
    SELECT widget_type, 'impression'  AS stage, 1 AS stage_order, impressions  AS stage_count FROM funnel_by_widget
    UNION ALL
    SELECT widget_type, 'interaction', 2, interactions FROM funnel_by_widget
    UNION ALL
    SELECT widget_type, 'completion',  3, completions  FROM funnel_by_widget
)

SELECT
    fl.widget_type,
    fl.stage,
    fl.stage_count,

    -- Previous stage's count, via LAG, partitioned per widget_type
    -- and ordered by funnel position
    LAG(fl.stage_count) OVER (
        PARTITION BY fl.widget_type ORDER BY fl.stage_order
    ) AS previous_stage_count,

    -- Drop-off % from the previous stage to this one
    ROUND(
        100.0 * (
            LAG(fl.stage_count) OVER (PARTITION BY fl.widget_type ORDER BY fl.stage_order)
            - fl.stage_count
        ) / NULLIF(LAG(fl.stage_count) OVER (PARTITION BY fl.widget_type ORDER BY fl.stage_order), 0),
        1
    ) AS dropoff_pct_from_previous_stage,

    wr.overall_completion_rate_pct,
    wr.overall_completion_rank

FROM funnel_long fl
JOIN widget_ranks wr ON fl.widget_type = wr.widget_type
ORDER BY fl.widget_type, fl.stage_order;

-- ================================================================
-- 4. RETENTION COHORTS: % of users active in week N after signup
-- ================================================================
-- Business question: If 100 users sign up in a given week, how many
-- are still active 1 week later? 4 weeks later? This is the single
-- most important metric for judging whether a gamification product
-- actually keeps fans coming back, vs. just acquiring one-time tries.
--
-- Technique:
--   - Cohort = the calendar week a user signed up in (for grouping
--     users into readable cohorts on a dashboard).
--   - week_number, however, is calculated as days-since-the-user's-
--     OWN-signup-date / 7 -- a true rolling window anchored to each
--     individual user, NOT a calendar-week bucket. This matters:
--     bucketing week_number by calendar week instead would make
--     week 0 artificially short for anyone who signs up mid-week
--     (e.g. a Saturday signup only gets 1-2 days counted as "week 0"
--     under calendar-week bucketing), understating week-0 retention
--     and inflating week-1 by comparison. Anchoring to the user's
--     own signup date avoids that distortion entirely.
-- ================================================================

WITH user_cohort AS (
    SELECT
        user_id,
        signup_date,
        DATE_TRUNC('week', signup_date)::date AS cohort_week
    FROM users
),

user_activity_weeks AS (
    -- For each user, every distinct week_number (0, 1, 2, ...) in
    -- which they had at least one session, measured as whole weeks
    -- elapsed since THEIR OWN signup_date.
    SELECT DISTINCT
        s.user_id,
        uc.cohort_week,
        FLOOR(
            EXTRACT(EPOCH FROM (s.app_open_time - uc.signup_date)) / (7 * 86400)
        )::int AS week_number
    FROM sessions s
    JOIN user_cohort uc ON s.user_id = uc.user_id
    WHERE s.app_open_time >= uc.signup_date   -- defensive: ignore any pre-signup noise
),

cohort_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM user_cohort
    GROUP BY cohort_week
),

retention_counts AS (
    SELECT
        cohort_week,
        week_number,
        COUNT(DISTINCT user_id) AS active_users
    FROM user_activity_weeks
    WHERE week_number BETWEEN 0 AND 8   -- cap at 8 weeks for a readable table
    GROUP BY cohort_week, week_number
)

SELECT
    rc.cohort_week,
    cs.cohort_size,
    rc.week_number,
    rc.active_users,
    ROUND(100.0 * rc.active_users / cs.cohort_size, 1) AS retention_pct
FROM retention_counts rc
JOIN cohort_sizes cs ON rc.cohort_week = cs.cohort_week
ORDER BY rc.cohort_week, rc.week_number;

-- ================================================================
-- 5. LEADERBOARD: top users ranked by total points
-- ================================================================
-- Business question: Who are the platform's most engaged "super-fans"?
-- This directly powers the user-facing leaderboard widget itself, and
-- is also useful internally for identifying power users worth
-- rewarding, surveying, or studying for engagement patterns.
--
-- Technique: RANK() (not ROW_NUMBER or DENSE_RANK) so that tied point
-- totals share the same rank and the next rank skips appropriately
-- (e.g. two users tied at rank 3 means the next user is rank 5, not
-- 4) -- this matches how leaderboards conventionally display ties.
-- ================================================================

SELECT
    RANK() OVER (ORDER BY up.total_points DESC) AS leaderboard_rank,
    u.user_id,
    u.country,
    u.device_type,
    up.total_points,
    up.last_updated,

    -- bonus context: how many badges has this user earned?
    (
        SELECT COUNT(*)
        FROM badges b
        WHERE b.user_id = u.user_id
    ) AS badge_count

FROM user_points up
JOIN users u ON up.user_id = u.user_id
ORDER BY leaderboard_rank
LIMIT 10;

-- ================================================================
-- 6. ROLLING 7-DAY ACTIVE USERS
-- ================================================================
-- Business question: Smoothed out day-to-day noise, is the platform
-- trending up or down in engagement? A rolling 7-day window is the
-- standard way product teams view this -- raw DAU is too spiky
-- (weekday/weekend, evening-vs-morning patterns) to spot a real trend
-- by eye, so this smooths it into a single trend line.
--
-- Technique: a true window function with an explicit frame clause
-- (RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW), as
-- opposed to Query 1's correlated-subquery approach -- this is the
-- more idiomatic window-function way to express a rolling window,
-- and performs better at scale since the window function avoids
-- re-scanning the table once per row.
-- ================================================================

WITH daily_unique_users AS (
    -- One row per day, with the distinct user_id's active that day
    -- collected into an array so we can union them across a rolling
    -- window without double-counting a user active on multiple days.
    SELECT
        DATE(app_open_time) AS activity_date,
        ARRAY_AGG(DISTINCT user_id) AS active_user_ids
    FROM sessions
    GROUP BY DATE(app_open_time)
),

daily_dau AS (
    SELECT
        activity_date,
        CARDINALITY(active_user_ids) AS dau
    FROM daily_unique_users
)

SELECT
    du.activity_date,
    du.dau,

    -- Rolling 7-day unique active users: union all user_id arrays
    -- from the preceding 6 days through today, then count distinct.
    -- A correlated subquery is used here (not a window function)
    -- because de-duplicating user_ids across a rolling window of
    -- ARRAYS isn't expressible as a simple window frame -- we need
    -- to flatten and re-aggregate per row, which window functions
    -- alone can't do.
    (
        SELECT COUNT(DISTINCT uid)
        FROM (
            SELECT UNNEST(d2.active_user_ids) AS uid
            FROM daily_unique_users d2
            WHERE d2.activity_date BETWEEN du.activity_date - INTERVAL '6 days'
                                        AND du.activity_date
        ) sub
    ) AS rolling_7d_active_users,

    -- Simple rolling 7-day AVERAGE of daily DAU (smoothed trend line),
    -- using a genuine window frame -- this is the textbook "rolling
    -- average" window function pattern.
    ROUND(
        AVG(du.dau) OVER (
            ORDER BY du.activity_date
            RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
        ),
        1
    ) AS rolling_7d_avg_dau

FROM daily_dau du
ORDER BY du.activity_date;

-- ================================================================
-- 7. (STRETCH) POWER USER SEGMENTATION
-- ================================================================
-- Business question: We know engagement follows a power-law curve
-- (validated during data generation: top 20% of users drive ~78% of
-- sessions). This query quantifies that same pattern in terms of
-- POINTS and COMPLETIONS instead of raw session count -- the metrics
-- that actually matter for a gamification product's monetization and
-- retention strategy. If "casual" users contribute almost nothing,
-- that's a strong signal to invest retention/reward efforts on
-- "regular" users (the ones closest to becoming power users), not
-- on casual one-time tries who are unlikely to convert regardless.
--
-- Technique: NTILE(3) window function to split users into 3 equal-
-- sized engagement tiers by total_points, then aggregate each tier's
-- share of total points and completions.
-- ================================================================

WITH user_tiers AS (
    SELECT
        up.user_id,
        up.total_points,
        NTILE(3) OVER (ORDER BY up.total_points ASC) AS tier_number
    FROM user_points up
),

tier_labeled AS (
    SELECT
        user_id,
        total_points,
        CASE tier_number
            WHEN 1 THEN 'Casual'
            WHEN 2 THEN 'Regular'
            WHEN 3 THEN 'Power User'
        END AS engagement_tier
    FROM user_tiers
),

tier_completions AS (
    SELECT
        tl.engagement_tier,
        COUNT(*) FILTER (WHERE we.event_type = 'completion') AS completions
    FROM tier_labeled tl
    JOIN widget_events we ON we.user_id = tl.user_id
    GROUP BY tl.engagement_tier
)

SELECT
    tl.engagement_tier,
    COUNT(DISTINCT tl.user_id) AS num_users,
    SUM(tl.total_points) AS total_points,
    ROUND(100.0 * SUM(tl.total_points) / SUM(SUM(tl.total_points)) OVER (), 1) AS pct_of_all_points,
    tc.completions,
    ROUND(100.0 * tc.completions / SUM(tc.completions) OVER (), 1) AS pct_of_all_completions,
    ROUND(AVG(tl.total_points), 1) AS avg_points_per_user
FROM tier_labeled tl
JOIN tier_completions tc ON tl.engagement_tier = tc.engagement_tier
GROUP BY tl.engagement_tier, tc.completions
ORDER BY
    CASE tl.engagement_tier
        WHEN 'Casual' THEN 1
        WHEN 'Regular' THEN 2
        WHEN 'Power User' THEN 3
    END;

    -- ================================================================
-- 8. (STRETCH) ENGAGEMENT RATE BY COUNTRY AND DEVICE
-- ================================================================
-- Business question: For a global sports/media platform, does
-- engagement differ meaningfully by country or device type? This
-- matters for prioritizing platform investment (iOS vs Android vs
-- Web) and for localization/regional content decisions.
--
-- Technique: a single query with TWO independent breakdowns combined
-- via UNION ALL, each tagged with a 'breakdown_type' label so both
-- views can be filtered/compared from one result set -- a common
-- pattern for feeding a single flexible dashboard filter.
-- ================================================================

WITH device_breakdown AS (
    SELECT
        'device_type' AS breakdown_type,
        u.device_type AS segment,
        COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
        COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE we.event_type = 'interaction')
            / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'impression'), 0),
            1
        ) AS engagement_rate_pct
    FROM widget_events we
    JOIN users u ON we.user_id = u.user_id
    GROUP BY u.device_type
),

country_breakdown AS (
    SELECT
        'country' AS breakdown_type,
        u.country AS segment,
        COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
        COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE we.event_type = 'interaction')
            / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'impression'), 0),
            1
        ) AS engagement_rate_pct
    FROM widget_events we
    JOIN users u ON we.user_id = u.user_id
    GROUP BY u.country
)

SELECT * FROM device_breakdown
UNION ALL
SELECT * FROM country_breakdown
ORDER BY breakdown_type, engagement_rate_pct DESC;