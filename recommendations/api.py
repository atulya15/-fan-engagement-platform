"""
recommendations/api.py
========================
Recommendation endpoints as a FastAPI router, mounted by api/main.py
(the single deployed backend for Phase 6). Kept in recommendations/
rather than api/ since it's tightly coupled to recommendations/serve.py
-- the router is the "public interface" of this module, same as how
metrics/ exposes Python functions and dashboard/app.py calls them.

Model training (recommendations/serve.py:train_recommender_state)
happens ONCE, triggered by api/main.py's lifespan hook via
`init_state()` below -- not per-request. ALS + LightGBM training takes
~2 minutes on this dataset, fine as a startup cost, wrong as a
per-request cost.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from recommendations.serve import get_recommendation, train_recommender_state

STATE: dict = {}


def init_state():
    """Called once from api/main.py's lifespan startup hook."""
    print("Training recommendation models (one-time startup cost, ~2 min)...")
    STATE.update(train_recommender_state())
    print("Recommendation models ready.")


router = APIRouter(tags=["recommendations"])


class RecommendationItem(BaseModel):
    widget_id: int
    widget_type: str
    score: float


class RecommendationResponse(BaseModel):
    user_id: int
    method_used: str
    is_cold_start: bool
    why: str
    recommendations: list[RecommendationItem]


@router.get("/recommend", response_model=RecommendationResponse)
def recommend(user_id: int, n: int = 10):
    if "hybrid_model" not in STATE:
        raise HTTPException(503, "Models still training, try again shortly.")
    result = get_recommendation(STATE, user_id, n=n)
    if result is None:
        raise HTTPException(404, f"user_id {user_id} not found")
    return result


@router.get("/recommend/health")
def health():
    return {"status": "ok", "models_loaded": "hybrid_model" in STATE}
