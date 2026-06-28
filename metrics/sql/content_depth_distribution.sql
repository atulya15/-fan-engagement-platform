-- ================================================================
-- Engagement depth distribution (interaction -> completion latency)
-- ================================================================
-- Business question: this product has no video/article content with
-- a "watch time" concept -- the closest analog to "how deeply did a
-- user engage with this piece of content" is how long they spent
-- between tapping into a widget (interaction) and finishing it
-- (completion). A poll should be near-instant; a multi-question
-- trivia widget should take noticeably longer -- if it doesn't, that's
-- a sign users are rushing through without really engaging.
-- ================================================================

WITH completion_latency AS (
    SELECT
        w.widget_type,
        i.event_timestamp AS interaction_ts,
        c.event_timestamp AS completion_ts,
        EXTRACT(EPOCH FROM (c.event_timestamp - i.event_timestamp)) AS latency_seconds
    FROM widget_events i
    JOIN widget_events c
        ON c.widget_id = i.widget_id
       AND c.user_id = i.user_id
       AND c.session_id = i.session_id
       AND c.event_type = 'completion'
       AND c.event_timestamp >= i.event_timestamp
    JOIN widgets w ON w.widget_id = i.widget_id
    WHERE i.event_type = 'interaction'
)

SELECT
    widget_type,
    COUNT(*) AS n_completed_interactions,
    ROUND(AVG(latency_seconds)::numeric, 1) AS avg_latency_sec,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_seconds))::numeric, 1) AS median_latency_sec,
    ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_seconds))::numeric, 1) AS p95_latency_sec
FROM completion_latency
GROUP BY widget_type
ORDER BY median_latency_sec DESC;
