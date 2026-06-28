"""
recommendations/api.py
========================
FastAPI service exposing the hybrid recommender as `/recommend`. Model
training (recommendations/serve.py:train_recommender_state) happens
ONCE at startup via a lifespan hook, not per-request -- ALS + LightGBM
training takes ~2 minutes on this dataset, which is fine as a startup
cost and completely wrong as a per-request cost.

Run with:
    uvicorn recommendations.api:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from recommendations.serve import get_recommendation, train_recommender_state

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Training recommendation models (one-time startup cost, ~2 min)...")
    STATE.update(train_recommender_state())
    print("Models ready.")
    yield
    STATE.clear()


app = FastAPI(title="Fan Engagement Platform — Recommendations API", lifespan=lifespan)


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


@app.get("/recommend", response_model=RecommendationResponse)
def recommend(user_id: int, n: int = 10):
    if "hybrid_model" not in STATE:
        raise HTTPException(503, "Models still training, try again shortly.")
    result = get_recommendation(STATE, user_id, n=n)
    if result is None:
        raise HTTPException(404, f"user_id {user_id} not found")
    return result


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": "hybrid_model" in STATE}
