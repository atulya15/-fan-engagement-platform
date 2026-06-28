-- ================================================================
-- Individual widget performance ranking (creator-level analog)
-- ================================================================
-- Business question: this product has no creator_id -- there's no
-- "who made this content" dimension to rank. The closest meaningful
-- analog is ranking individual WIDGETS (each widget is the unit of
-- "a piece of content" here), to answer "which specific widgets are
-- over/under-performing, and is that explained by widget_type/sport,
-- or is something widget-specific going on (bad copy, confusing UI,
-- launched at a bad time)?"
--
-- A minimum impression threshold filters out widgets that simply
-- haven't accumulated enough exposure yet to have a reliable
-- engagement rate -- without it, a brand-new widget with 3 impressions
-- and 2 interactions would show a meaningless 67% engagement rate at
-- the very top of the leaderboard. Applied in Python (content.py),
-- not hardcoded here, so the threshold is a tunable parameter.
-- ================================================================

WITH widget_stats AS (
    SELECT
        w.widget_id,
        w.name,
        w.widget_type,
        w.sport,
        w.launch_date,
        COUNT(*) FILTER (WHERE we.event_type = 'impression')  AS impressions,
        COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
        COUNT(*) FILTER (WHERE we.event_type = 'completion')  AS completions,
        SUM(we.points_earned) AS total_points_generated
    FROM widgets w
    LEFT JOIN widget_events we ON we.widget_id = w.widget_id
    GROUP BY w.widget_id, w.name, w.widget_type, w.sport, w.launch_date
)

SELECT
    widget_id, name, widget_type, sport, launch_date,
    impressions, interactions, completions, total_points_generated,
    ROUND(100.0 * interactions / NULLIF(impressions, 0), 1) AS engagement_rate_pct
FROM widget_stats
ORDER BY engagement_rate_pct DESC;
