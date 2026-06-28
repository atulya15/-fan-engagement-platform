-- ================================================================
-- Growth metrics: new vs. returning vs. resurrected users per week,
-- weekly churn, and the Quick Ratio
-- ================================================================
-- Business question: is the platform actually growing, or is new-user
-- acquisition just masking churn? Quick Ratio = (new + resurrected) /
-- churned answers this directly: a ratio > 1 means more users are
-- coming in (fresh or returning from a gap) than are leaving that
-- week; < 1 means the platform is shrinking even if raw signups look
-- fine on their own.
--
-- Definitions (all computed on a CALENDAR-WEEK grain, distinct from
-- the per-user signup-anchored cohort weeks used in retention.py):
--   - new:         active this week, and this is their signup week.
--   - returning:   active this week AND active last week, signed up
--                  before this week (continuously engaged).
--   - resurrected: active this week, signed up before this week, but
--                  NOT active last week (came back after a gap of at
--                  least one full week -- whether or not they had any
--                  prior activity at all; a user who signed up and
--                  only activates weeks later is folded into this
--                  bucket too, since the practical effect on growth
--                  is identical: someone who wasn't engaging is now
--                  engaging).
--   - churned:     active LAST week, NOT active this week.
-- ================================================================

WITH user_signup_week AS (
    SELECT user_id, DATE_TRUNC('week', signup_date)::date AS signup_week
    FROM users
),

user_weeks AS (
    -- Every (user_id, calendar_week) pair where the user had >=1 session.
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('week', app_open_time)::date AS activity_week
    FROM sessions
),

all_weeks AS (
    SELECT generate_series(
        (SELECT MIN(activity_week) FROM user_weeks),
        (SELECT MAX(activity_week) FROM user_weeks),
        INTERVAL '7 days'
    )::date AS week
),

classified AS (
    -- A LEFT JOIN against user_weeks for "the prior calendar week" rather
    -- than a per-row correlated EXISTS subquery -- the correlated version
    -- forces a nested-loop re-scan of user_weeks for every one of the
    -- ~320K (user, week) rows, which is what made this query crawl. A
    -- single hash join computes the same thing once.
    SELECT
        w.week,
        uw.user_id,
        usw.signup_week,
        (usw.signup_week = w.week) AS is_new,
        (prev.user_id IS NOT NULL) AS was_active_prev_week
    FROM all_weeks w
    JOIN user_weeks uw ON uw.activity_week = w.week
    JOIN user_signup_week usw ON usw.user_id = uw.user_id
    LEFT JOIN user_weeks prev
        ON prev.user_id = uw.user_id AND prev.activity_week = w.week - INTERVAL '7 days'
),

weekly_growth AS (
    SELECT
        week,
        COUNT(*) FILTER (WHERE is_new) AS new_users,
        COUNT(*) FILTER (WHERE NOT is_new AND was_active_prev_week) AS returning_users,
        COUNT(*) FILTER (WHERE NOT is_new AND NOT was_active_prev_week) AS resurrected_users,
        COUNT(*) AS total_active_users
    FROM classified
    GROUP BY week
),

weekly_churn AS (
    -- Users active in the PRIOR week who are not active this week.
    SELECT
        w.week,
        COUNT(DISTINCT p.user_id) AS churned_users
    FROM all_weeks w
    JOIN user_weeks p ON p.activity_week = w.week - INTERVAL '7 days'
    LEFT JOIN user_weeks c ON c.user_id = p.user_id AND c.activity_week = w.week
    WHERE c.user_id IS NULL
    GROUP BY w.week
)

SELECT
    g.week,
    g.new_users,
    g.returning_users,
    g.resurrected_users,
    g.total_active_users,
    COALESCE(ch.churned_users, 0) AS churned_users,
    ROUND(
        (g.new_users + g.resurrected_users)::numeric / NULLIF(ch.churned_users, 0),
        2
    ) AS quick_ratio
FROM weekly_growth g
LEFT JOIN weekly_churn ch ON ch.week = g.week
ORDER BY g.week;
