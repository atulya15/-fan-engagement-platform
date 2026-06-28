"""
recommendations/evaluate.py
=============================
Offline evaluation: Recall@10 and NDCG@10 on a TEMPORAL train/test
split (never random -- see data.py's temporal_split docstring), for
each of the three recommendation methods, so they can be honestly
compared rather than each shown in isolation.

CATALOG-SIZE CAVEAT (repeated from data.py since this is where the
metrics actually get computed): only 60 widgets exist, so Top-10
covers ~17% of the whole catalog. Recall@10/NDCG@10 values here are
NOT comparable to a production recommender with a catalog of
thousands -- the methodology generalizes, the absolute numbers don't.
"""

import math
import random

import numpy as np
import pandas as pd

from recommendations.collaborative import recommend_cf, train_als
from recommendations.content_based import (
    build_item_similarity,
    recommend_for_new_user,
    recommend_similar_to_history,
)
from recommendations.data import (
    build_interaction_matrix,
    build_widget_features,
    load_events,
    temporal_split,
    test_ground_truth,
)
from recommendations.hybrid import (
    build_training_examples,
    compute_feature_lookups,
    recommend_hybrid,
    train_hybrid_ranker,
)


def recall_at_k(recommended: list[int], ground_truth: set[int], k: int = 10) -> float:
    if not ground_truth:
        return float("nan")
    hits = len(set(recommended[:k]) & ground_truth)
    return hits / len(ground_truth)


def ndcg_at_k(recommended: list[int], ground_truth: set[int], k: int = 10) -> float:
    if not ground_truth:
        return float("nan")
    dcg = sum(1.0 / math.log2(i + 2) for i, item in enumerate(recommended[:k]) if item in ground_truth)
    ideal_hits = min(len(ground_truth), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else float("nan")


def run_evaluation(max_test_users: int = 800, seed: int = 42) -> dict:
    """
    Runs all three methods (CF-only, content-only, hybrid) on the same
    temporally-held-out test users and returns a comparison table plus
    a warm/cold breakdown, since the methods' relative performance
    should differ specifically on cold-start users -- that's the point
    of having a content-based fallback at all.
    """
    rng = random.Random(seed)

    events = load_events()
    train_df, test_df = temporal_split(events)
    ground_truth = test_ground_truth(test_df)

    widget_meta = events.drop_duplicates("widget_id")[["widget_id", "widget_type", "sport"]]
    widget_ids = sorted(widget_meta["widget_id"].unique())
    widget_type_map = widget_meta.set_index("widget_id")["widget_type"].to_dict()
    widget_features = build_widget_features(widget_meta)
    item_sim = build_item_similarity(widget_features)

    train_user_ids = sorted(train_df["user_id"].unique())
    train_matrix, user_idx, widget_idx = build_interaction_matrix(train_df, train_user_ids, widget_ids)
    inv_widget_idx = {v: k for k, v in widget_idx.items()}

    als_model = train_als(train_matrix)

    # Precompute cf_scores for every (warm train user) x (widget) pair
    # via the factor dot product -- cheap, since it's a small dense
    # matrix (n_train_users x 60), not 10K x 60K.
    user_factors = als_model.user_factors
    item_factors = als_model.item_factors
    score_matrix = user_factors @ item_factors.T
    cf_scores = {}
    for uid, ui in user_idx.items():
        for wid, wi in widget_idx.items():
            cf_scores[(uid, wid)] = float(score_matrix[ui, wi])

    lookups = compute_feature_lookups(train_df, item_sim)

    cf_score_lookup_for_training = {k: v for k, v in cf_scores.items()}
    train_examples = build_training_examples(train_df, cf_score_lookup_for_training, lookups, widget_ids)
    hybrid_model = train_hybrid_ranker(train_examples)

    user_segment_map = events.drop_duplicates("user_id").set_index("user_id")["user_segment"].to_dict()
    user_channel_map = events.drop_duplicates("user_id").set_index("user_id")["acquisition_channel"].to_dict()
    user_history = train_df[train_df["event_type"].isin(["interaction", "completion"])] \
        .groupby("user_id")["widget_id"].apply(set).to_dict()

    test_users = list(ground_truth.keys())
    if len(test_users) > max_test_users:
        test_users = rng.sample(test_users, max_test_users)

    rows = []
    for user_id in test_users:
        gt = ground_truth[user_id]
        is_warm = user_id in user_idx
        seen = user_history.get(user_id, set())
        candidates = [w for w in widget_ids if w not in seen]

        # CF-only: literally cannot score a user it has no row for.
        if is_warm:
            cf_recs = [inv_widget_idx[i] for i, _ in recommend_cf(als_model, user_idx[user_id], train_matrix, n=10)]
        else:
            cf_recs = []

        # Content-only: this IS the cold-start handler, so it always produces something.
        if user_id in user_history:
            content_recs = recommend_similar_to_history(user_id, train_df, item_sim, n=10)
            if not content_recs:
                content_recs = recommend_for_new_user(user_channel_map.get(user_id, "organic"), train_df, n=10)
        else:
            content_recs = recommend_for_new_user(user_channel_map.get(user_id, "organic"), train_df, n=10)

        # Hybrid: degrades gracefully for cold users since cf_score defaults to 0
        # for any (user, widget) pair not in cf_scores.
        hybrid_ranked = recommend_hybrid(
            hybrid_model, user_id, candidates, user_segment_map.get(user_id, "free"),
            widget_type_map, cf_scores, lookups, n=10,
        )
        hybrid_recs = [w for w, _ in hybrid_ranked]

        rows.append({
            "user_id": user_id, "is_warm": is_warm,
            "cf_recall": recall_at_k(cf_recs, gt), "cf_ndcg": ndcg_at_k(cf_recs, gt),
            "content_recall": recall_at_k(content_recs, gt), "content_ndcg": ndcg_at_k(content_recs, gt),
            "hybrid_recall": recall_at_k(hybrid_recs, gt), "hybrid_ndcg": ndcg_at_k(hybrid_recs, gt),
        })

    results_df = pd.DataFrame(rows)

    summary = []
    for method in ["cf", "content", "hybrid"]:
        for segment_name, subset in [("all", results_df), ("warm_only", results_df[results_df["is_warm"]]),
                                      ("cold_only", results_df[~results_df["is_warm"]])]:
            summary.append({
                "method": method, "segment": segment_name, "n_users": len(subset),
                "recall_at_10": subset[f"{method}_recall"].mean(),
                "ndcg_at_10": subset[f"{method}_ndcg"].mean(),
            })

    return {
        "summary": pd.DataFrame(summary),
        "per_user": results_df,
        "n_test_users": len(test_users),
        "n_warm": int(results_df["is_warm"].sum()),
        "n_cold": int((~results_df["is_warm"]).sum()),
        "catalog_size": len(widget_ids),
    }
