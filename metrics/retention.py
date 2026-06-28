"""
metrics/retention.py
=====================
Retention metrics: the single most interview-scrutinized part of any
product analytics layer. Every function here is explicit about which
of the two retention definitions it computes, because conflating them
is the most common subtle bug in this space.

  - BOUNDED retention("returned ON day N"): noisy, but the textbook
    definition of Day-N retention.
  - UNBOUNDED retention ("active ON OR AFTER day N"): more forgiving,
    less noisy, usually the better choice for a health dashboard.

All cohort/day-N functions exclude users who haven't had the chance to
reach day N yet (censoring) rather than counting them as failures —
this is the bug already caught once in this project's history
(see README "Design Notes") and is guarded against explicitly here.
"""

import pandas as pd

from metrics.db import run_sql_file


def day_n_retention() -> pd.DataFrame:
    """Bounded vs. unbounded retention at Day 1/3/7/14/30."""
    return run_sql_file("day_n_retention.sql")


def cohort_retention_matrix() -> pd.DataFrame:
    """
    Signup-week cohort x weeks-since-signup (0-11) retention matrix.
    `retention_pct` is NULL for cells the cohort hasn't lived long
    enough to reach yet (censored) — distinct from a true 0%.
    """
    return run_sql_file("cohort_retention_matrix.sql")


def cohort_retention_pivot() -> pd.DataFrame:
    """
    Same data as cohort_retention_matrix(), reshaped into a wide
    cohort_week x week_number grid — the heatmap-ready format for the
    Phase 3 dashboard (rows = cohorts, columns = week_number).
    """
    long_df = cohort_retention_matrix()
    return long_df.pivot(index="cohort_week", columns="week_number", values="retention_pct")


def rolling_28d_retention() -> pd.DataFrame:
    """% of each cohort active at any point in the trailing 28 days —
    catches cohorts that retained early but have since gone dormant."""
    return run_sql_file("rolling_retention.sql")


def segment_retention() -> pd.DataFrame:
    """Day-7 / Day-30 unbounded retention broken down by
    acquisition_channel and device_type."""
    return run_sql_file("segment_retention.sql")
