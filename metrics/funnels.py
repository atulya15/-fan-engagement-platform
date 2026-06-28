"""
metrics/funnels.py
===================
Core engagement funnel: signup -> first view -> first engagement ->
repeat engagement -> premium conversion. Reports both overall
("% of all signups") and step-specific ("% of the previous step")
conversion rates, since they answer different questions.
"""

import pandas as pd

from metrics.db import run_sql_file


def funnel_overview() -> pd.DataFrame:
    """
    Step-by-step funnel with median time-between-steps.

    premium_conversion has no median time-to-convert: user_segment is
    a derived snapshot (computed once from final behavior), not an
    event with its own timestamp, so "time since signup to conversion"
    isn't knowable from this schema -- reported as NULL rather than
    silently dropped.
    """
    return run_sql_file("funnel_overview.sql")


def funnel_by_channel() -> pd.DataFrame:
    """Same funnel, broken down by acquisition_channel — reveals
    whether different channels leak at different funnel stages."""
    return run_sql_file("funnel_by_segment.sql")
