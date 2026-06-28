-- ================================================================
-- Day-N retention: bounded vs unbounded
-- ================================================================
-- Business question: of users who signed up, what % came back on
-- day N specifically (bounded), and what % were still active by day N
-- or later (unbounded)? These answer different questions and people
-- conflate them constantly:
--   - Bounded ("returned ON day N"):    did they come back exactly
--     N days after signup? Tight, noisy at the single-day level, but
--     the textbook definition of "Day-N retention."
--   - Unbounded ("returned ON OR AFTER day N"): are they still alive
--     as of day N, whether or not day N itself had a session? Less
--     noisy, more forgiving, often what a churn/health dashboard
--     actually wants to show ("X% of users are still around by week 1").
--
-- A user can only be counted in either denominator once they've HAD
-- the chance to reach day N — i.e. (today - signup_date) >= N days.
-- Users who signed up too recently to have reached day N yet are
-- excluded from that day's denominator entirely (censored), not
-- counted as failures. Omitting this check is the single most common
-- retention-calculation bug: it silently understates retention for
-- every N as recent signups flood in and haven't had time to return.
-- ================================================================

WITH user_days AS (
    -- Every distinct day-since-signup on which a user had a session,
    -- anchored to their OWN signup date (not a calendar boundary).
    SELECT DISTINCT
        s.user_id,
        u.signup_date,
        FLOOR(EXTRACT(EPOCH FROM (s.app_open_time - u.signup_date)) / 86400)::int AS day_number
    FROM sessions s
    JOIN users u ON u.user_id = s.user_id
    WHERE s.app_open_time >= u.signup_date
),

target_days AS (
    SELECT unnest(ARRAY[1, 3, 7, 14, 30]) AS n
),

eligible AS (
    -- Only users old enough to have reached day N count toward N's
    -- denominator -- this is the censoring guard described above.
    SELECT
        t.n,
        u.user_id
    FROM target_days t
    CROSS JOIN users u
    WHERE u.signup_date <= (SELECT MAX(app_open_time) FROM sessions) - (t.n || ' days')::interval
)

SELECT
    e.n AS day_n,
    COUNT(DISTINCT e.user_id) AS eligible_users,

    COUNT(DISTINCT ud_bounded.user_id) AS returned_on_day_n,
    ROUND(100.0 * COUNT(DISTINCT ud_bounded.user_id) / NULLIF(COUNT(DISTINCT e.user_id), 0), 1)
        AS bounded_retention_pct,

    COUNT(DISTINCT ud_unbounded.user_id) AS active_on_or_after_day_n,
    ROUND(100.0 * COUNT(DISTINCT ud_unbounded.user_id) / NULLIF(COUNT(DISTINCT e.user_id), 0), 1)
        AS unbounded_retention_pct

FROM eligible e
LEFT JOIN user_days ud_bounded
    ON ud_bounded.user_id = e.user_id AND ud_bounded.day_number = e.n
LEFT JOIN user_days ud_unbounded
    ON ud_unbounded.user_id = e.user_id AND ud_unbounded.day_number >= e.n
GROUP BY e.n
ORDER BY e.n;
