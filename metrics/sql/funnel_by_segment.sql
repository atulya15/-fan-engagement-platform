-- ================================================================
-- Engagement funnel broken down by acquisition_channel
-- ================================================================
-- Business question: does the funnel leak at a different stage
-- depending on how the user was acquired? E.g. paid_social users
-- might view content fine (they clicked an ad promising it) but
-- engage far less (lower intent) -- a different shape of drop-off
-- than, say, organic users who view less often but engage more when
-- they do.
-- ================================================================

WITH first_view AS (
    SELECT user_id, MIN(event_timestamp) AS first_view_ts
    FROM widget_events
    WHERE event_type = 'impression'
    GROUP BY user_id
),

-- Single windowed pass, not a correlated per-user subquery -- see
-- funnel_overview.sql for why that matters at this row count.
interactions_ranked AS (
    SELECT
        user_id,
        event_timestamp,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_timestamp) AS rn
    FROM widget_events
    WHERE event_type = 'interaction'
),

interactions_agg AS (
    SELECT
        user_id,
        MIN(event_timestamp) FILTER (WHERE rn = 1) AS first_engagement_ts,
        MIN(event_timestamp) FILTER (WHERE rn = 2) AS second_interaction_ts
    FROM interactions_ranked
    GROUP BY user_id
),

user_step_times AS (
    SELECT
        u.user_id,
        u.acquisition_channel,
        u.user_segment,
        fv.first_view_ts,
        ia.first_engagement_ts,
        ia.second_interaction_ts
    FROM users u
    LEFT JOIN first_view fv ON fv.user_id = u.user_id
    LEFT JOIN interactions_agg ia ON ia.user_id = u.user_id
),

funnel_flags AS (
    SELECT
        acquisition_channel,
        (first_view_ts IS NOT NULL) AS reached_view,
        (first_engagement_ts IS NOT NULL) AS reached_engagement,
        (
            second_interaction_ts IS NOT NULL
            AND DATE(second_interaction_ts) > DATE(first_engagement_ts)
        ) AS reached_repeat_engagement,
        (user_segment = 'premium') AS reached_premium
    FROM user_step_times
)

SELECT
    acquisition_channel,
    COUNT(*) AS signups,
    COUNT(*) FILTER (WHERE reached_view) AS first_view,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reached_view) / COUNT(*), 1) AS pct_first_view,
    COUNT(*) FILTER (WHERE reached_engagement) AS first_engagement,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reached_engagement) / COUNT(*), 1) AS pct_first_engagement,
    COUNT(*) FILTER (WHERE reached_repeat_engagement) AS repeat_engagement,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reached_repeat_engagement) / COUNT(*), 1) AS pct_repeat_engagement,
    COUNT(*) FILTER (WHERE reached_premium) AS premium_conversion,
    ROUND(100.0 * COUNT(*) FILTER (WHERE reached_premium) / COUNT(*), 1) AS pct_premium_conversion
FROM funnel_flags
GROUP BY acquisition_channel
ORDER BY pct_premium_conversion DESC;
