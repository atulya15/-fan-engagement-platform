-- ================================================================
-- Session frequency & duration distribution
-- ================================================================
-- Business question: how long do sessions typically last, and how
-- often does a user come back? Medians/percentiles matter more than
-- the mean here — a handful of multi-hour outlier sessions would
-- otherwise drag the average session length up to a misleading number.
--
-- Technique: PERCENTILE_CONT for true interpolated percentiles (not
-- PERCENTILE_DISC, which snaps to an actual observed value — CONT is
-- the standard choice for continuous metrics like duration in seconds).
-- ================================================================

WITH session_durations AS (
    SELECT
        session_id,
        user_id,
        EXTRACT(EPOCH FROM (app_close_time - app_open_time)) AS duration_seconds
    FROM sessions
    WHERE app_close_time IS NOT NULL
),

sessions_per_user AS (
    SELECT user_id, COUNT(*) AS session_count
    FROM sessions
    GROUP BY user_id
)

SELECT
    (SELECT COUNT(*) FROM sessions) AS total_sessions,
    (SELECT COUNT(DISTINCT user_id) FROM sessions) AS distinct_users,

    ROUND((SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds) FROM session_durations)::numeric, 1)
        AS median_session_duration_sec,
    ROUND((SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY duration_seconds) FROM session_durations)::numeric, 1)
        AS p75_session_duration_sec,
    ROUND((SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) FROM session_durations)::numeric, 1)
        AS p95_session_duration_sec,

    ROUND((SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY session_count) FROM sessions_per_user)::numeric, 1)
        AS median_sessions_per_user,
    ROUND((SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY session_count) FROM sessions_per_user)::numeric, 1)
        AS p75_sessions_per_user,
    ROUND((SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY session_count) FROM sessions_per_user)::numeric, 1)
        AS p95_sessions_per_user;
