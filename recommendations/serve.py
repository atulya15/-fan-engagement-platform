"""
recommendations/serve.py
==========================
Shared "train once, serve many" logic used by BOTH recommendations/api.py
(the FastAPI service) and the dashboard's Recommendations tab, so the
two don't duplicate the same ~150s training pipeline with two
different implementations that could drift out of sync.
"""

from recommendations.collaborative import recommend_cf, train_als
from recommendations.content_based import build_item_similarity, recommend_for_new_user
from recommendations.data import build_interaction_matrix, build_widget_features, load_events, temporal_split
from recommendations.hybrid import build_training_examples, compute_feature_lookups, recommend_hybrid, train_hybrid_ranker


def train_recommender_state() -> dict:
    """Trains ALS + the hybrid LightGBM ranker on the TRAIN split and
    returns everything needed to serve recommendations. Expensive
    (~2 min) -- call once, cache the result, never call per-request."""
    events = load_events()
    train_df, _test_df = temporal_split(events)

    widget_meta = events.drop_duplicates("widget_id")[["widget_id", "widget_type", "sport"]]
    widget_ids = sorted(widget_meta["widget_id"].unique())
    widget_type_map = widget_meta.set_index("widget_id")["widget_type"].to_dict()
    widget_features = build_widget_features(widget_meta)
    item_sim = build_item_similarity(widget_features)

    train_user_ids = sorted(train_df["user_id"].unique())
    train_matrix, user_idx, widget_idx = build_interaction_matrix(train_df, train_user_ids, widget_ids)
    als_model = train_als(train_matrix)

    user_factors, item_factors = als_model.user_factors, als_model.item_factors
    score_matrix = user_factors @ item_factors.T
    cf_scores = {(uid, wid): float(score_matrix[ui, wi])
                 for uid, ui in user_idx.items() for wid, wi in widget_idx.items()}

    lookups = compute_feature_lookups(train_df, item_sim)
    train_examples = build_training_examples(train_df, cf_scores, lookups, widget_ids)
    hybrid_model = train_hybrid_ranker(train_examples)

    user_history = train_df[train_df["event_type"].isin(["interaction", "completion"])] \
        .groupby("user_id")["widget_id"].apply(set).to_dict()
    user_segment_map = events.drop_duplicates("user_id").set_index("user_id")["user_segment"].to_dict()
    user_channel_map = events.drop_duplicates("user_id").set_index("user_id")["acquisition_channel"].to_dict()

    return dict(
        train_df=train_df, als_model=als_model, train_matrix=train_matrix,
        user_idx=user_idx, widget_idx=widget_idx, item_sim=item_sim,
        widget_ids=widget_ids, widget_type_map=widget_type_map,
        cf_scores=cf_scores, lookups=lookups, hybrid_model=hybrid_model,
        user_history=user_history, user_segment_map=user_segment_map,
        user_channel_map=user_channel_map,
    )


def get_recommendation(state: dict, user_id: int, n: int = 10) -> dict:
    """The actual serving logic: cold-start users go through the
    content-based fallback, warm users through the hybrid ranker."""
    if user_id not in state["user_segment_map"]:
        return None

    seen = state["user_history"].get(user_id, set())
    candidates = [w for w in state["widget_ids"] if w not in seen]
    segment = state["user_segment_map"][user_id]
    channel = state["user_channel_map"].get(user_id, "organic")
    is_cold_start = user_id not in state["user_history"]

    if is_cold_start:
        method_used = "content_based_cold_start"
        why = (f"No interaction history for this user (cold start) — falling back to the top engaged "
               f"widgets within their acquisition-channel cohort ('{channel}').")
        widget_ids = recommend_for_new_user(channel, state["train_df"], n=n)
        ranked = [(w, 1.0) for w in widget_ids]
    else:
        method_used = "hybrid"
        why = ("Ranked by a LightGBM model combining collaborative-filtering score, content similarity to this "
               "user's history, segment-level content-type affinity, content recency, and time-of-day match.")
        ranked = recommend_hybrid(
            state["hybrid_model"], user_id, candidates, segment,
            state["widget_type_map"], state["cf_scores"], state["lookups"], n=n,
        )

    items = [{"widget_id": wid, "widget_type": state["widget_type_map"].get(wid, "unknown"), "score": float(score)}
             for wid, score in ranked]
    return {"user_id": user_id, "method_used": method_used, "is_cold_start": is_cold_start,
            "why": why, "recommendations": items}
