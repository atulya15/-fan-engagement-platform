-- ================================================================
-- Content engagement rate by widget_type AND sport (category)
-- ================================================================
-- Business question: which content format AND which content category
-- actually hold attention? Crossed together (not just one or the
-- other) because a format that works great in one category (e.g.
-- predictions for Football, a sport with frequent score changes) may
-- not generalize to another (predictions for Tennis, which has fewer
-- discrete scoring events to predict).
-- ================================================================

SELECT
    w.widget_type,
    w.sport AS category,
    COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
    COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
    COUNT(*) FILTER (WHERE we.event_type = 'completion')  AS completions,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE we.event_type = 'interaction')
        / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'impression'), 0),
        1
    ) AS engagement_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE we.event_type = 'completion')
        / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'interaction'), 0),
        1
    ) AS completion_rate_pct
FROM widgets w
JOIN widget_events we ON we.widget_id = w.widget_id
GROUP BY w.widget_type, w.sport
ORDER BY engagement_rate_pct DESC;
