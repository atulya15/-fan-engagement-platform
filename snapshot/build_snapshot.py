"""
snapshot/build_snapshot.py
============================
Builds the single JSON snapshot the Next.js dashboard site (site/) is
statically generated from. Pure orchestration -- every number here
comes from the existing metrics/, experimentation/, and
recommendations/ modules; no new computation logic lives in this file.

A dashboard site cannot have a 60-second load (several underlying
queries take 40-150s on free-tier Supabase, observed directly during
Phase 4). This script runs once, offline, and writes a static JSON
file the site reads at build time -- the same "precompute, don't
recompute on every page load" pattern already used for
recommendations/eval_results.json in Phase 5.

Run with:
    python snapshot/build_snapshot.py
"""

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from metrics.db import run_query
from metrics.engagement import dau_wau_mau, session_stats
from metrics.funnels import funnel_overview, funnel_by_channel
from metrics.growth import weekly_growth
from metrics.retention import (
    cohort_retention_matrix,
    day_n_retention,
    rolling_28d_retention,
    segment_retention,
)
from metrics.content import widget_performance, engagement_by_type_and_category
from experimentation.analyze import (
    analyze_feed_experiment,
    analyze_onboarding_experiment,
    analyze_push_experiment,
)


def to_native(obj):
    """Recursively converts numpy scalars/arrays and dataclasses into
    plain JSON-serializable Python types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_native(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (np.generic,)):
        return obj.item()
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return [to_native(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


def pd_isna(v):
    return v != v  # NaN check without importing pandas here


def df_records(df) -> list[dict]:
    """Generic DataFrame -> list-of-dicts, NaN-safe, for tabular data
    that doesn't need a bespoke chart-ready shape."""
    return [
        {k: (None if pd_isna(v) else to_native(v)) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


def build_retention_heatmap(cohort_df) -> dict:
    cohort_df = cohort_df.copy()
    cohort_df["cohort_week"] = cohort_df["cohort_week"].astype(str)
    cohorts = sorted(cohort_df["cohort_week"].unique())
    weeks = sorted(cohort_df["week_number"].unique())
    grid = []
    for cohort in cohorts:
        row = cohort_df[cohort_df["cohort_week"] == cohort].sort_values("week_number")
        grid.append({
            "cohort_week": cohort,
            "cohort_size": int(row["cohort_size"].iloc[0]),
            "values": [None if pd_isna(v) else float(v) for v in row["retention_pct"].tolist()],
        })
    return {"cohorts": cohorts, "weeks": [int(w) for w in weeks], "grid": grid}


def build_funnel(funnel_df) -> dict:
    return {
        "steps": funnel_df["step"].tolist(),
        "users_reached": [int(v) for v in funnel_df["users_reached"].tolist()],
        "pct_of_signups": [float(v) for v in funnel_df["pct_of_signups"].tolist()],
        "pct_of_previous_step": [None if pd_isna(v) else float(v) for v in funnel_df["pct_of_previous_step"].tolist()],
    }


def build_growth(growth_df) -> dict:
    growth_df = growth_df.copy()
    growth_df["week"] = growth_df["week"].astype(str)
    return {
        "weeks": growth_df["week"].tolist(),
        "new_users": [int(v) for v in growth_df["new_users"].tolist()],
        "returning_users": [int(v) for v in growth_df["returning_users"].tolist()],
        "resurrected_users": [int(v) for v in growth_df["resurrected_users"].tolist()],
        "churned_users": [int(v) for v in growth_df["churned_users"].tolist()],
        "quick_ratio": [None if pd_isna(v) else float(v) for v in growth_df["quick_ratio"].tolist()],
    }


def build_dau_series(dwm_df) -> dict:
    dwm_df = dwm_df.copy()
    dwm_df["activity_date"] = dwm_df["activity_date"].astype(str)
    return {
        "dates": dwm_df["activity_date"].tolist(),
        "dau": [int(v) for v in dwm_df["dau"].tolist()],
        "wau": [int(v) for v in dwm_df["wau"].tolist()],
        "mau": [int(v) for v in dwm_df["mau"].tolist()],
        "stickiness": [None if pd_isna(v) else float(v) for v in dwm_df["stickiness_dau_mau"].tolist()],
    }


def build_experiment(result: dict) -> dict:
    out = {
        "name": result["name"],
        "primary_metric": result["primary_metric"],
        "primary": result["primary"],
        "guardrail_metric": result["guardrail_metric"],
        "guardrail": result["guardrail"],
        "guardrail_ok": result["guardrail_ok"],
        "required_n_per_arm": result["required_n_per_arm"],
        "decision": result["decision"],
        "segment_results": [
            {"segment": s["segment"], "result": s["result"]}
            for s in result.get("segment_results", [])
        ],
    }
    if "cuped" in result:
        out["cuped_variance_reduction_pct"] = result["cuped"]["var_reduction_pct"]
    if "sequential_peeks" in result:
        out["sequential_peeks"] = result["sequential_peeks"]
    if "sequential_alphas" in result:
        out["sequential_alphas"] = result["sequential_alphas"]
    if "cohens_d" in result:
        out["cohens_d"] = result["cohens_d"]
    return to_native(out)


def main():
    print("Loading hero counts...")
    counts = run_query("SELECT (SELECT COUNT(*) FROM users) AS total_users, "
                        "(SELECT COUNT(*) FROM widget_events) AS total_events").iloc[0]

    print("Loading engagement metrics...")
    dwm = dau_wau_mau()
    sstats = session_stats()

    print("Loading retention metrics...")
    cohort = cohort_retention_matrix()
    day_n = day_n_retention()
    rolling = rolling_28d_retention()
    seg_retention = segment_retention()

    print("Loading funnel...")
    funnel = funnel_overview()
    funnel_channel = funnel_by_channel()

    print("Loading growth...")
    growth = weekly_growth()

    print("Loading content/widget performance...")
    widgets = widget_performance().head(15)
    content_by_type = engagement_by_type_and_category()

    print("Running feed personalization experiment analysis...")
    feed_experiment = analyze_feed_experiment()

    print("Running onboarding experiment analysis...")
    onboarding_experiment = analyze_onboarding_experiment()

    print("Running push notification experiment analysis (~1-2 min)...")
    push_experiment = analyze_push_experiment()

    eval_path = Path(__file__).parent.parent / "recommendations" / "eval_results.json"
    with open(eval_path) as f:
        recommendation_eval = json.load(f)

    snapshot = {
        "hero": {
            "total_users": int(counts["total_users"]),
            "total_events": int(counts["total_events"]),
            "simulation_months": 12,
            "avg_stickiness_30d": round(float(dwm.iloc[:-1]["stickiness_dau_mau"].tail(30).mean()), 3),
            "median_sessions_per_user": float(sstats["median_sessions_per_user"].iloc[0]),
        },
        "engagement": {
            "dau_series": build_dau_series(dwm),
            "session_stats": to_native(sstats.iloc[0].to_dict()),
        },
        "retention": {
            "heatmap": build_retention_heatmap(cohort),
            "day_n": df_records(day_n),
            "rolling_28d": df_records(rolling.assign(cohort_week=rolling["cohort_week"].astype(str))),
            "by_segment": df_records(seg_retention),
        },
        "funnel": {
            "overall": build_funnel(funnel),
            "by_channel": df_records(funnel_channel),
        },
        "growth": build_growth(growth),
        "content": {
            "top_widgets": df_records(widgets),
            "by_type_category": df_records(content_by_type),
        },
        "experiments": {
            "feed": build_experiment(feed_experiment),
            "onboarding": build_experiment(onboarding_experiment),
            "push": build_experiment(push_experiment),
        },
        "recommendation_eval": recommendation_eval,
    }

    out_path = Path(__file__).parent.parent / "site" / "data" / "snapshot.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(to_native(snapshot), f, indent=2)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
