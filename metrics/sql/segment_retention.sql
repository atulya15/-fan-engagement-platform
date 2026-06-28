-- ================================================================
-- Segment-level retention: Day-7 and Day-30 unbounded retention,
-- broken down by acquisition_channel and by device_type
-- ================================================================
-- Business question: does retention differ by HOW a user found the
-- product, or WHAT device they're on? This is the query that turns
-- "our retention is 45%" into an actionable insight: "our retention
-- is 45% overall, but referral users retain at 60% and influencer
-- users at 28% -- stop spending on influencer acquisition, it doesn't
-- stick."
--
-- Uses the same censoring guard as day_n_retention.sql (only count
-- users old enough to have reached day N), and the same UNBOUNDED
-- definition ("active on or after day N") since that's the more
-- forgiving, less noisy metric a segment breakdown should use.
-- ================================================================

WITH user_days AS (
    SELECT DISTINCT
        s.user_id,
        FLOOR(EXTRACT(EPOCH FROM (s.app_open_time - u.signup_date)) / 86400)::int AS day_number
    FROM sessions s
    JOIN users u ON u.user_id = s.user_id
    WHERE s.app_open_time >= u.signup_date
),

target_days AS (
    SELECT unnest(ARRAY[7, 30]) AS n
),

eligible AS (
    SELECT t.n, u.user_id, u.acquisition_channel, u.device_type
    FROM target_days t
    CROSS JOIN users u
    WHERE u.signup_date <= (SELECT MAX(app_open_time) FROM sessions) - (t.n || ' days')::interval
),

retained AS (
    SELECT e.n, e.user_id, e.acquisition_channel, e.device_type
    FROM eligible e
    JOIN user_days ud ON ud.user_id = e.user_id AND ud.day_number >= e.n
)

SELECT
    'acquisition_channel' AS breakdown_type,
    e.acquisition_channel AS segment,
    e.n AS day_n,
    COUNT(DISTINCT e.user_id) AS eligible_users,
    COUNT(DISTINCT r.user_id) AS retained_users,
    ROUND(100.0 * COUNT(DISTINCT r.user_id) / NULLIF(COUNT(DISTINCT e.user_id), 0), 1) AS retention_pct
FROM eligible e
LEFT JOIN retained r ON r.n = e.n AND r.user_id = e.user_id
GROUP BY e.acquisition_channel, e.n

UNION ALL

SELECT
    'device_type' AS breakdown_type,
    e.device_type AS segment,
    e.n AS day_n,
    COUNT(DISTINCT e.user_id) AS eligible_users,
    COUNT(DISTINCT r.user_id) AS retained_users,
    ROUND(100.0 * COUNT(DISTINCT r.user_id) / NULLIF(COUNT(DISTINCT e.user_id), 0), 1) AS retention_pct
FROM eligible e
LEFT JOIN retained r ON r.n = e.n AND r.user_id = e.user_id
GROUP BY e.device_type, e.n

ORDER BY breakdown_type, day_n, retention_pct DESC;
