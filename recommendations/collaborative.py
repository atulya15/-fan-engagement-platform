"""
recommendations/collaborative.py
==================================
Collaborative filtering baseline via Alternating Least Squares (ALS)
on implicit feedback (the `implicit` library). No explicit ratings
exist in this product (no star ratings on a poll) -- ALS on weighted
implicit signals (impression/interaction/completion) is the standard
approach when all you have is "did they engage, and how much."
"""

import numpy as np
from implicit.als import AlternatingLeastSquares
from scipy.sparse import csr_matrix


def train_als(train_matrix: csr_matrix, factors: int = 32, regularization: float = 0.05,
              iterations: int = 20, alpha: float = 5.0) -> AlternatingLeastSquares:
    """
    `alpha` scales raw event-weight counts into ALS's confidence
    formulation (confidence = 1 + alpha * weight) -- higher alpha makes
    the model trust observed interactions more relative to the implicit
    "everything unobserved is a weak negative" assumption ALS makes.
    """
    model = AlternatingLeastSquares(factors=factors, regularization=regularization,
                                     iterations=iterations, random_state=42)
    confidence_matrix = (train_matrix * alpha).astype(np.float32)
    model.fit(confidence_matrix)
    return model


def recommend_cf(model: AlternatingLeastSquares, user_row_idx: int, train_matrix: csr_matrix,
                  n: int = 10) -> list[tuple[int, float]]:
    """Top-N (item_index, score) pairs for a user, excluding items
    they've already interacted with in training (implicit's
    `filter_already_liked_items` does this automatically)."""
    ids, scores = model.recommend(user_row_idx, train_matrix[user_row_idx], N=n,
                                   filter_already_liked_items=True)
    return list(zip(ids.tolist(), scores.tolist()))
