-- ================================================================
-- Events per session + content consumption rate by widget type
-- ================================================================
-- Business question: how much does a typical session actually "do"
-- (events per session), and which widget types get the most exposure
-- relative to how many exist? Consumption rate = impressions per
-- widget of that type, normalizing for the fact that there may be more
-- poll widgets in the catalog than leaderboard widgets.
-- ================================================================

WITH events_per_session AS (
    SELECT
        s.session_id,
        COUNT(we.event_id) AS event_count
    FROM sessions s
    LEFT JOIN widget_events we ON we.session_id = s.session_id
    GROUP BY s.session_id
),

content_rate AS (
    SELECT
        w.widget_type,
        COUNT(DISTINCT w.widget_id) AS num_widgets,
        COUNT(*) FILTER (WHERE we.event_type = 'impression') AS total_impressions,
        ROUND(
            COUNT(*) FILTER (WHERE we.event_type = 'impression')::numeric
            / NULLIF(COUNT(DISTINCT w.widget_id), 0),
            1
        ) AS impressions_per_widget
    FROM widgets w
    LEFT JOIN widget_events we ON we.widget_id = w.widget_id
    GROUP BY w.widget_type
)

SELECT
    'events_per_session' AS metric_group,
    NULL AS widget_type,
    ROUND(AVG(event_count)::numeric, 2) AS avg_value,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY event_count))::numeric, 1) AS median_value,
    NULL::bigint AS num_widgets,
    NULL::bigint AS total_impressions
FROM events_per_session

UNION ALL

SELECT
    'content_consumption_rate' AS metric_group,
    widget_type,
    impressions_per_widget AS avg_value,
    NULL AS median_value,
    num_widgets,
    total_impressions
FROM content_rate
ORDER BY metric_group, widget_type;
