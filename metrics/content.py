"""
metrics/content.py
====================
Content metrics, honestly adapted to this product's actual shape: no
video/article content (so no literal "watch time") and no creator_id
(so no literal "creator performance"). Each function's docstring
states the substitution made and why it's the right analog, not a
forced fit.
"""

import pandas as pd

from metrics.db import run_sql_file


def engagement_by_type_and_category() -> pd.DataFrame:
    """Engagement/completion rate crossed by widget_type AND sport —
    whether a format works depends on which content category it's
    paired with, not just the format alone."""
    return run_sql_file("content_engagement_by_type_category.sql")


def engagement_depth_distribution() -> pd.DataFrame:
    """
    Interaction-to-completion latency, the watch-time analog for a
    widget-based product: how long a user actually spends finishing
    a widget once they start it, not just whether they finished it.
    """
    return run_sql_file("content_depth_distribution.sql")


def widget_performance(min_impressions: int = 200) -> pd.DataFrame:
    """
    Individual widget ranking by engagement rate and points generated
    — the creator-performance analog, since this product has no
    creator_id; the widget itself is the unit of "a piece of content."
    Filters to widgets with >= min_impressions to avoid ranking noise
    from widgets that haven't accumulated enough exposure yet.
    """
    df = run_sql_file("widget_performance.sql")
    return df[df["impressions"] >= min_impressions].reset_index(drop=True)
