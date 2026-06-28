"""
snapshot/build_snapshot.py
============================
Builds the single JSON snapshot the Next.js showcase site (site/) is
statically generated from. Pure orchestration -- every number here
comes from the existing metrics/, experimentation/, and
recommendations/ modules; no new computation logic lives in this file.

A showcase site cannot have a 60-second load (several underlying
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

from metrics.db import run_query
from metrics.engagement import dau_wau_mau, session_stats
from metrics.funnels import funnel_overview
from metrics.growth import weekly_growth
from metrics.retention import cohort_retention_matrix
from experimentation.analyze import analyze_push_experiment


def to_native(obj):
    """Recursively converts numpy scalars/arrays and dataclasses into
    plain JSON-serializable Python types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_native(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (np.generic,)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return [to_native(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


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


def pd_isna(v):
    return v != v  # NaN check without importing pandas here


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
        "quick_ratio": [None if pd_isna(v) else float(v) for v in growth_df["quick_ratio"].tolist()],
    }


def main():
    print("Loading hero counts...")
    counts = run_query("SELECT (SELECT COUNT(*) FROM users) AS total_users, "
                        "(SELECT COUNT(*) FROM widget_events) AS total_events").iloc[0]

    print("Loading engagement metrics...")
    dwm = dau_wau_mau()
    sstats = session_stats()

    print("Loading retention cohort matrix...")
    cohort = cohort_retention_matrix()

    print("Loading funnel...")
    funnel = funnel_overview()

    print("Loading growth...")
    growth = weekly_growth()

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
        "retention": build_retention_heatmap(cohort),
        "funnel": build_funnel(funnel),
        "growth": build_growth(growth),
        "experiment": to_native({
            "name": push_experiment["name"],
            "primary_metric": push_experiment["primary_metric"],
            "primary": push_experiment["primary"],
            "decision": push_experiment["decision"],
            "guardrail_ok": push_experiment["guardrail_ok"],
            "cuped_variance_reduction_pct": push_experiment["cuped"]["var_reduction_pct"],
            "sequential_peeks": push_experiment["sequential_peeks"],
            "sequential_alphas": push_experiment["sequential_alphas"],
        }),
        "recommendation_eval": recommendation_eval,
    }

    out_path = Path(__file__).parent.parent / "site" / "data" / "snapshot.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(to_native(snapshot), f, indent=2)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
