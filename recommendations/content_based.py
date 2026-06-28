"""
recommendations/content_based.py
==================================
Content-based fallback -- the cold-start handler. ALS (and any
collaborative method) needs interaction history to work; it has
nothing to say about a user who just signed up or a widget that just
launched. Content-based similarity needs no interaction history at
all, only item/user features, which is exactly why it's the standard
fallback for both cold-start cases.
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def build_item_similarity(widget_features: pd.DataFrame) -> pd.DataFrame:
    """Widget x widget cosine similarity over content features
    (widget_type + sport one-hots). Returns a labeled DataFrame so
    callers can index by widget_id directly."""
    sim = cosine_similarity(widget_features.to_numpy())
    return pd.DataFrame(sim, index=widget_features.index, columns=widget_features.index)


def recommend_for_new_user(acquisition_channel: str, train_df: pd.DataFrame, n: int = 10) -> list[int]:
    """
    COLD-START USER: no interaction history exists at all (e.g. a user
    who just signed up). Fall back to "what does this user's
    acquisition-channel cohort tend to engage with" -- a population-
    level prior, the standard new-user cold-start strategy when
    there's no per-user signal yet. Ranked by total interaction+
    completion volume within that cohort, not raw impressions (volume
    of genuine engagement, not just exposure).
    """
    cohort = train_df[
        (train_df["acquisition_channel"] == acquisition_channel)
        & (train_df["event_type"].isin(["interaction", "completion"]))
    ]
    if len(cohort) == 0:
        cohort = train_df[train_df["event_type"].isin(["interaction", "completion"])]
    top = cohort["widget_id"].value_counts().head(n)
    return top.index.tolist()


def recommend_similar_to_history(user_id: int, train_df: pd.DataFrame, item_sim: pd.DataFrame,
                                  n: int = 10) -> list[int]:
    """
    WARM USER, content-based path: rank candidate widgets by their
    average content similarity to widgets this user has already
    engaged with, excluding widgets already seen. Used as one of the
    three methods compared in evaluation (content-only), and as a
    component signal in the hybrid ranker.
    """
    user_history = train_df[
        (train_df["user_id"] == user_id) & (train_df["event_type"].isin(["interaction", "completion"]))
    ]["widget_id"].unique()
    if len(user_history) == 0:
        return []

    seen = set(train_df[train_df["user_id"] == user_id]["widget_id"].unique())
    candidates = [w for w in item_sim.index if w not in seen]
    scores = {w: item_sim.loc[w, user_history].mean() for w in candidates}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [w for w, _ in ranked[:n]]


def similar_widgets_for_new_content(widget_id: int, item_sim: pd.DataFrame, n: int = 5) -> list[tuple[int, float]]:
    """
    COLD-START CONTENT: a brand-new widget has zero interaction history
    -- nothing to collaboratively filter on. Answer "which EXISTING
    widgets is this one most like" via content similarity alone, which
    tells a content/product team who to surface a new widget to (the
    audience of its most similar existing widgets) without waiting for
    it to accumulate its own engagement data first.
    """
    if widget_id not in item_sim.index:
        return []
    sims = item_sim.loc[widget_id].drop(widget_id).sort_values(ascending=False)
    return list(zip(sims.head(n).index.tolist(), sims.head(n).to_numpy().tolist()))
