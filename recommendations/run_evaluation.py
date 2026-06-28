"""
recommendations/run_evaluation.py
====================================
Computes the offline Recall@10/NDCG@10 evaluation once and saves the
summary table to recommendations/eval_results.json. Recommender
evaluation is a batch process in real systems too -- nothing computes
this on every page load -- so the dashboard reads this static file
rather than re-running ~150s of ALS + LightGBM training on every visit.

Run with:
    python recommendations/run_evaluation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from recommendations.evaluate import run_evaluation

if __name__ == "__main__":
    print("Running recommendation evaluation (~2-3 min)...")
    results = run_evaluation(max_test_users=800)

    output = {
        "summary": results["summary"].to_dict(orient="records"),
        "n_test_users": results["n_test_users"],
        "n_warm": results["n_warm"],
        "n_cold": results["n_cold"],
        "catalog_size": results["catalog_size"],
    }

    out_path = Path(__file__).parent / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to {out_path}")
    print(results["summary"].to_string())
