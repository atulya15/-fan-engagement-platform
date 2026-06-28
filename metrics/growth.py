"""
metrics/growth.py
==================
Growth metrics: new vs. returning vs. resurrected users per week,
weekly churn, and the Quick Ratio — the metric that tells you whether
growth is real or just acquisition masking churn.
"""

import pandas as pd

from metrics.db import run_sql_file


def weekly_growth() -> pd.DataFrame:
    """
    Per-week new/returning/resurrected/churned users and Quick Ratio.

    Business definition: Quick Ratio = (new + resurrected) / churned.
    > 1.0 means the platform gained more users that week (fresh
    signups plus people coming back from a gap) than it lost to churn
    — net growth. < 1.0 means it's shrinking even if the signup number
    alone looks healthy. This is the metric that catches "vanity
    growth" — strong top-of-funnel acquisition hiding a leaky bottom.
    """
    return run_sql_file("growth_metrics.sql")
