"""
verify_data.py
==============
Sanity-checks the generated data: row counts, orphaned foreign keys,
and whether the power-law engagement distribution and funnel
conversion rates landed the way we designed them.
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()


def run(label, query):
    cur.execute(query)
    rows = cur.fetchall()
    print(f"\n--- {label} ---")
    for row in rows:
        print(row)


# 1. Row counts
run("Row counts", """
    SELECT 'users' AS table_name, COUNT(*) FROM users
    UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
    UNION ALL SELECT 'widgets', COUNT(*) FROM widgets
    UNION ALL SELECT 'widget_events', COUNT(*) FROM widget_events
    UNION ALL SELECT 'user_points', COUNT(*) FROM user_points
    UNION ALL SELECT 'badges', COUNT(*) FROM badges;
""")

# 2. Orphaned foreign keys (should all return 0)
run("Orphaned sessions (user_id not in users)", """
    SELECT COUNT(*) FROM sessions s
    LEFT JOIN users u ON s.user_id = u.user_id
    WHERE u.user_id IS NULL;
""")

run("Orphaned widget_events (widget_id not in widgets)", """
    SELECT COUNT(*) FROM widget_events we
    LEFT JOIN widgets w ON we.widget_id = w.widget_id
    WHERE w.widget_id IS NULL;
""")

run("Orphaned widget_events (user_id not in users)", """
    SELECT COUNT(*) FROM widget_events we
    LEFT JOIN users u ON we.user_id = u.user_id
    WHERE u.user_id IS NULL;
""")

run("Orphaned widget_events (session_id not in sessions)", """
    SELECT COUNT(*) FROM widget_events we
    LEFT JOIN sessions s ON we.session_id = s.session_id
    WHERE s.session_id IS NULL;
""")

run("Users with no user_points row (should be 0)", """
    SELECT COUNT(*) FROM users u
    LEFT JOIN user_points up ON u.user_id = up.user_id
    WHERE up.user_id IS NULL;
""")

# 3. Power-law engagement check: top 20% of users by session count
#    should account for a large majority of total sessions
run("Power-law check: session count distribution", """
    WITH user_sessions AS (
        SELECT user_id, COUNT(*) AS session_count
        FROM sessions
        GROUP BY user_id
    ),
    ranked AS (
        SELECT user_id, session_count,
               NTILE(5) OVER (ORDER BY session_count DESC) AS quintile
        FROM user_sessions
    )
    SELECT quintile,
           COUNT(*) AS num_users,
           SUM(session_count) AS total_sessions,
           ROUND(100.0 * SUM(session_count) / SUM(SUM(session_count)) OVER (), 1) AS pct_of_all_sessions
    FROM ranked
    GROUP BY quintile
    ORDER BY quintile;
""")

# 4. Funnel sanity: impressions > interactions > completions overall
run("Funnel totals by event_type", """
    SELECT event_type, COUNT(*) AS event_count
    FROM widget_events
    GROUP BY event_type
    ORDER BY
        CASE event_type
            WHEN 'impression' THEN 1
            WHEN 'interaction' THEN 2
            WHEN 'completion' THEN 3
        END;
""")

# 5. Funnel by widget_type (should show polls converting better than trivia)
run("Conversion rate by widget_type", """
    SELECT
        w.widget_type,
        COUNT(*) FILTER (WHERE we.event_type = 'impression') AS impressions,
        COUNT(*) FILTER (WHERE we.event_type = 'interaction') AS interactions,
        COUNT(*) FILTER (WHERE we.event_type = 'completion') AS completions,
        ROUND(100.0 * COUNT(*) FILTER (WHERE we.event_type = 'interaction')
              / NULLIF(COUNT(*) FILTER (WHERE we.event_type = 'impression'), 0), 1) AS impression_to_interaction_pct
    FROM widget_events we
    JOIN widgets w ON we.widget_id = w.widget_id
    GROUP BY w.widget_type
    ORDER BY w.widget_type;
""")

# 6. Signup distribution shape (front-loaded check)
run("Signups by month", """
    SELECT DATE_TRUNC('month', signup_date)::date AS signup_month,
           COUNT(*) AS num_signups
    FROM users
    GROUP BY 1
    ORDER BY 1;
""")

# 7. Date range sanity
run("Date range checks", """
    SELECT
        MIN(signup_date) AS earliest_signup,
        MAX(signup_date) AS latest_signup
    FROM users;
""")

cur.close()
conn.close()
print("\n Verification complete.")