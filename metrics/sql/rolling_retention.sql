-- ================================================================
-- Rolling 28-day retention by cohort
-- ================================================================
-- Business question: distinct from Day-N retention (which anchors to
-- each user's own signup date and answers "are new users sticking
-- around"), rolling retention answers a different question: "of users
-- who signed up in week X, what fraction are STILL active RIGHT NOW"
-- -- i.e. active at any point in the most recent 28-day window,
-- regardless of how long ago they signed up. This is the metric that
-- catches a cohort that retained fine initially but has quietly gone
-- dormant since.
-- ================================================================

WITH user_cohort AS (
    SELECT user_id, DATE_TRUNC('week', signup_date)::date AS cohort_week
    FROM users
),

cohort_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM user_cohort
    GROUP BY cohort_week
),

recent_activity AS (
    SELECT DISTINCT s.user_id
    FROM sessions s
    WHERE s.app_open_time >= (SELECT MAX(app_open_time) FROM sessions) - INTERVAL '28 days'
)

SELECT
    cs.cohort_week,
    cs.cohort_size,
    COUNT(DISTINCT ra.user_id) AS active_last_28d,
    ROUND(100.0 * COUNT(DISTINCT ra.user_id) / cs.cohort_size, 1) AS rolling_28d_retention_pct
FROM cohort_sizes cs
JOIN user_cohort uc ON uc.cohort_week = cs.cohort_week
LEFT JOIN recent_activity ra ON ra.user_id = uc.user_id
GROUP BY cs.cohort_week, cs.cohort_size
ORDER BY cs.cohort_week;
