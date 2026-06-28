-- ================================================================
-- DAU / WAU / MAU + stickiness ratio
-- ================================================================
-- Business question: how many unique users engage daily, weekly, and
-- monthly, and what fraction of monthly actives come back daily?
-- DAU/MAU stickiness is the headline "is this a daily habit or a
-- monthly errand" signal — below ~0.20 in a consumer app is a red
-- flag, above ~0.50 is best-in-class (Slack/WhatsApp territory).
--
-- Technique: one CTE derives "active day" per user once; DAU/WAU/MAU
-- are each a COUNT(DISTINCT user_id) over a different trailing window,
-- computed via correlated subquery (not a window function) because
-- de-duplicating users across a multi-day window isn't expressible as
-- a simple window frame.
-- ================================================================

WITH daily_activity AS (
    SELECT DATE(app_open_time) AS activity_date, user_id
    FROM sessions
    GROUP BY DATE(app_open_time), user_id
)

SELECT
    activity_date,

    COUNT(DISTINCT user_id) AS dau,

    (
        SELECT COUNT(DISTINCT user_id)
        FROM daily_activity d2
        WHERE d2.activity_date BETWEEN da.activity_date - INTERVAL '6 days'
                                    AND da.activity_date
    ) AS wau,

    (
        SELECT COUNT(DISTINCT user_id)
        FROM daily_activity d3
        WHERE d3.activity_date BETWEEN da.activity_date - INTERVAL '29 days'
                                    AND da.activity_date
    ) AS mau

FROM daily_activity da
GROUP BY activity_date
ORDER BY activity_date;
