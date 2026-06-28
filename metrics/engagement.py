"""
metrics/engagement.py
======================
Core engagement metrics: DAU/WAU/MAU + stickiness, session frequency/
duration distributions, events-per-session, and content consumption
rate by widget type.
"""

import pandas as pd

from metrics.db import run_sql_file


def dau_wau_mau() -> pd.DataFrame:
    """
    Daily/weekly/monthly active users, plus DAU/MAU stickiness.

    Business definition: stickiness = DAU / MAU on a given day — the
    fraction of a user's monthly cohort that's also active *today*.
    It's the standard "habit vs. errand" signal: under ~0.20 means most
    monthly users only show up once or twice a month (errand-like,
    classic for a utility app); above ~0.50 means most monthly users
    are showing up most days (habit-like, the Slack/WhatsApp band).
    There's no universal "good" number — it depends on the product's
    natural use frequency — but it's the right metric to track *over
    time* and benchmark against comparable products.
    """
    df = run_sql_file("dau_wau_mau.sql")
    df["stickiness_dau_mau"] = (df["dau"] / df["mau"]).round(3)
    return df


def session_stats() -> pd.DataFrame:
    """
    Session duration and session-frequency percentiles (median/p75/p95).

    Business definition: medians and percentiles, not the mean, because
    session duration is heavily right-skewed — a small number of very
    long sessions (someone leaving the app open) would otherwise drag
    the average up to a number that doesn't represent a typical visit.
    """
    return run_sql_file("session_stats.sql")


def events_and_content_rate() -> pd.DataFrame:
    """
    Events per session (how much a typical visit actually does) and
    content consumption rate by widget_type (impressions per widget of
    that type, normalized for catalog size differences).
    """
    return run_sql_file("events_per_session_and_content_rate.sql")
