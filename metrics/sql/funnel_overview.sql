-- ================================================================
-- Core engagement funnel: signup -> first view -> first engagement
-- -> repeat engagement -> premium conversion
-- ================================================================
-- Business question: where do users actually drop off? Mapped onto
-- this product's widget model:
--   signup              -> account created
--   first_view          -> first widget impression (content was shown)
--   first_engagement     -> first interaction (tapped/voted/answered)
--   repeat_engagement    -> a SECOND interaction, on a different day
--                           than the first -- this is the real
--                           "habit forming" signal, not just a second
--                           tap in the same first session
--   premium_conversion   -> user_segment = 'premium'
--
-- Two conversion rates are reported per step: conversion FROM SIGNUP
-- (the overall funnel, what % of all signups reach this far) and
-- conversion FROM THE PREVIOUS STEP (the step-specific drop-off, what
-- a PM would act on -- "70% who viewed never engaged" is actionable;
-- "70% of all signups never engaged" conflates a top-of-funnel and a
-- mid-funnel problem into one number).
--
-- premium_conversion has no time-to-convert: user_segment is a derived
-- snapshot (computed once, post-hoc, from final behavior), not an
-- event with its own timestamp, so "time since signup to conversion"
-- isn't knowable from this schema. Flagged explicitly with NULL rather
-- than silently omitted.
-- ================================================================

WITH first_view AS (
    -- Single pass over impressions, not a per-user correlated lookup.
    SELECT user_id, MIN(event_timestamp) AS first_view_ts
    FROM widget_events
    WHERE event_type = 'impression'
    GROUP BY user_id
),

-- A single PARTITION BY window pass ranks every user's interactions,
-- letting us grab the 1st and 2nd interaction timestamps in one scan
-- of widget_events -- not a correlated subquery re-run per user (that
-- pattern is what made growth_metrics.sql crawl before it was fixed;
-- same fix applied here pre-emptively).
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
        u.signup_date,
        u.user_segment,
        fv.first_view_ts,
        ia.first_engagement_ts,
        ia.second_interaction_ts
    FROM users u
    LEFT JOIN first_view fv ON fv.user_id = u.user_id
    LEFT JOIN interactions_agg ia ON ia.user_id = u.user_id
),

-- "Repeat engagement" requires the 2nd interaction to fall on a
-- DIFFERENT calendar day than the 1st -- otherwise a user tapping two
-- different polls in the same five-minute session would count as
-- having formed a "repeat habit," which overstates the signal.
funnel_flags AS (
    SELECT
        user_id,
        signup_date,
        user_segment,
        first_view_ts,
        first_engagement_ts,
        second_interaction_ts,
        (first_view_ts IS NOT NULL) AS reached_view,
        (first_engagement_ts IS NOT NULL) AS reached_engagement,
        (
            second_interaction_ts IS NOT NULL
            AND DATE(second_interaction_ts) > DATE(first_engagement_ts)
        ) AS reached_repeat_engagement,
        (user_segment = 'premium') AS reached_premium
    FROM user_step_times
),

step_counts AS (
    SELECT
        COUNT(*) AS signup_count,
        COUNT(*) FILTER (WHERE reached_view) AS view_count,
        COUNT(*) FILTER (WHERE reached_engagement) AS engagement_count,
        COUNT(*) FILTER (WHERE reached_repeat_engagement) AS repeat_engagement_count,
        COUNT(*) FILTER (WHERE reached_premium) AS premium_count
    FROM funnel_flags
),

median_times AS (
    SELECT
        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (first_view_ts - signup_date)) / 3600
        ) FILTER (WHERE reached_view))::numeric, 1) AS median_hours_signup_to_view,

        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (first_engagement_ts - first_view_ts)) / 3600
        ) FILTER (WHERE reached_engagement))::numeric, 1) AS median_hours_view_to_engagement,

        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (second_interaction_ts - first_engagement_ts)) / 3600
        ) FILTER (WHERE reached_repeat_engagement))::numeric, 1) AS median_hours_engagement_to_repeat
    FROM funnel_flags
)

SELECT
    step, step_order, users_reached,
    ROUND(100.0 * users_reached / sc.signup_count, 1) AS pct_of_signups,
    ROUND(100.0 * users_reached / NULLIF(LAG(users_reached) OVER (ORDER BY step_order), 0), 1)
        AS pct_of_previous_step,
    median_hours_from_previous_step
FROM (
    SELECT 'signup'             AS step, 1 AS step_order, signup_count AS users_reached, NULL::numeric AS median_hours_from_previous_step FROM step_counts
    UNION ALL
    SELECT 'first_view',         2, view_count,               mt.median_hours_signup_to_view        FROM step_counts, median_times mt
    UNION ALL
    SELECT 'first_engagement',   3, engagement_count,          mt.median_hours_view_to_engagement     FROM step_counts, median_times mt
    UNION ALL
    SELECT 'repeat_engagement',  4, repeat_engagement_count,   mt.median_hours_engagement_to_repeat   FROM step_counts, median_times mt
    UNION ALL
    SELECT 'premium_conversion', 5, premium_count,              NULL                                   FROM step_counts
) steps
CROSS JOIN step_counts sc
ORDER BY step_order;
