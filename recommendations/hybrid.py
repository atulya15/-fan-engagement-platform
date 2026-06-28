"""
recommendations/hybrid.py
===========================
Hybrid ranker: a LightGBM binary classifier that combines the
collaborative-filtering score, content similarity, segment affinity,
time-of-day match, and content recency into a single ranking score --
rather than relying on any one signal alone. Trained on the TRAIN
period's positive (user engaged) examples plus randomly sampled
negatives, never touching the TEST period (same temporal-split
discipline as the CF evaluation).
"""

import random

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier


def _hour_bucket(hour: int) -> str:
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def compute_feature_lookups(train_df: pd.DataFrame, item_sim: pd.DataFrame) -> dict:
    """Precomputes the per-user and per-widget lookups the feature
    builder needs, once, rather than recomputing them per training row."""
    engaged = train_df[train_df["event_type"].isin(["interaction", "completion"])]

    # Segment x widget_type affinity: engagement rate of each segment
    # toward each widget_type, used as the "segment match" feature.
    segment_type_counts = engaged.groupby(["user_segment", "widget_type"]).size()
    segment_totals = engaged.groupby("user_segment").size()
    segment_type_affinity = (segment_type_counts / segment_totals).to_dict()

    # Widget recency (days since launch) and popularity, as of the
    # train/test cutoff -- a static snapshot, not per-row recomputed.
    cutoff = train_df["event_timestamp"].max()
    widget_recency = (
        train_df.drop_duplicates("widget_id").set_index("widget_id")["launch_date"]
        .apply(lambda d: max((cutoff - d).days, 0))
        .to_dict()
    )
    widget_popularity = engaged["widget_id"].value_counts().to_dict()

    # Dominant hour-of-day bucket per user and per widget.
    train_df = train_df.copy()
    train_df["hour_bucket"] = train_df["event_timestamp"].dt.hour.apply(_hour_bucket)
    user_hour = train_df.groupby("user_id")["hour_bucket"].agg(lambda s: s.value_counts().idxmax()).to_dict()
    widget_hour = train_df.groupby("widget_id")["hour_bucket"].agg(lambda s: s.value_counts().idxmax()).to_dict()

    # Per-user engaged-widget set, for the content-similarity feature.
    user_history = engaged.groupby("user_id")["widget_id"].apply(set).to_dict()

    return {
        "segment_type_affinity": segment_type_affinity,
        "widget_recency": widget_recency,
        "widget_popularity": widget_popularity,
        "user_hour": user_hour,
        "widget_hour": widget_hour,
        "user_history": user_history,
        "item_sim": item_sim,
    }


def build_features(user_id: int, widget_id: int, user_segment: str, widget_type: str,
                    cf_score: float, lookups: dict) -> dict:
    history = lookups["user_history"].get(user_id, set())
    item_sim = lookups["item_sim"]
    if history and widget_id in item_sim.index:
        valid_history = [w for w in history if w in item_sim.columns]
        content_sim = item_sim.loc[widget_id, valid_history].mean() if valid_history else 0.0
    else:
        content_sim = 0.0

    segment_affinity = lookups["segment_type_affinity"].get((user_segment, widget_type), 0.0)
    recency_days = lookups["widget_recency"].get(widget_id, 365)
    popularity = lookups["widget_popularity"].get(widget_id, 0)
    time_match = int(lookups["user_hour"].get(user_id) == lookups["widget_hour"].get(widget_id))

    return {
        "cf_score": cf_score,
        "content_sim": content_sim,
        "segment_affinity": segment_affinity,
        "widget_recency_days": recency_days,
        "widget_popularity": popularity,
        "time_of_day_match": time_match,
    }


def build_training_examples(train_df: pd.DataFrame, cf_scores: dict, lookups: dict,
                             widget_ids: list[int], negative_ratio: int = 3,
                             seed: int = 42) -> pd.DataFrame:
    """
    Positive examples: every (user, widget) the user genuinely engaged
    with in TRAIN (interaction/completion). Negative examples: widgets
    a user did NOT engage with, sampled at `negative_ratio`x the
    positive count -- standard implicit-feedback ranking setup, since
    there's no observed explicit negative class otherwise.
    """
    rng = random.Random(seed)
    engaged = train_df[train_df["event_type"].isin(["interaction", "completion"])]
    user_meta = train_df.drop_duplicates("user_id").set_index("user_id")["user_segment"].to_dict()
    widget_meta = train_df.drop_duplicates("widget_id").set_index("widget_id")["widget_type"].to_dict()

    positives = engaged[["user_id", "widget_id"]].drop_duplicates()
    positives["label"] = 1

    seen_by_user = engaged.groupby("user_id")["widget_id"].apply(set).to_dict()
    neg_rows = []
    for user_id, group in positives.groupby("user_id"):
        seen = seen_by_user.get(user_id, set())
        candidates = [w for w in widget_ids if w not in seen]
        n_neg = min(len(group) * negative_ratio, len(candidates))
        if n_neg == 0:
            continue
        sampled = rng.sample(candidates, n_neg)
        neg_rows.extend((user_id, w) for w in sampled)
    negatives = pd.DataFrame(neg_rows, columns=["user_id", "widget_id"])
    negatives["label"] = 0

    examples = pd.concat([positives, negatives], ignore_index=True)
    feature_rows = []
    for row in examples.itertuples(index=False):
        feats = build_features(
            row.user_id, row.widget_id,
            user_meta.get(row.user_id, "free"), widget_meta.get(row.widget_id, "poll"),
            cf_scores.get((row.user_id, row.widget_id), 0.0), lookups,
        )
        feats["user_id"] = row.user_id
        feats["widget_id"] = row.widget_id
        feats["label"] = row.label
        feature_rows.append(feats)

    return pd.DataFrame(feature_rows)


FEATURE_COLUMNS = ["cf_score", "content_sim", "segment_affinity",
                    "widget_recency_days", "widget_popularity", "time_of_day_match"]


def train_hybrid_ranker(examples: pd.DataFrame) -> LGBMClassifier:
    model = LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                            random_state=42, verbosity=-1)
    model.fit(examples[FEATURE_COLUMNS], examples["label"])
    return model


def recommend_hybrid(model: LGBMClassifier, user_id: int, candidate_widgets: list[int],
                      user_segment: str, widget_type_map: dict, cf_scores: dict,
                      lookups: dict, n: int = 10) -> list[tuple[int, float]]:
    rows = []
    for widget_id in candidate_widgets:
        feats = build_features(user_id, widget_id, user_segment, widget_type_map.get(widget_id, "poll"),
                                cf_scores.get((user_id, widget_id), 0.0), lookups)
        rows.append(feats)
    feat_df = pd.DataFrame(rows)[FEATURE_COLUMNS]
    scores = model.predict_proba(feat_df)[:, 1]
    ranked = sorted(zip(candidate_widgets, scores), key=lambda kv: kv[1], reverse=True)
    return ranked[:n]
