"""
api/main.py
=============
The single deployed backend for Phase 6 (Render). Serves:
  - GET /snapshot — the precomputed JSON (snapshot/build_snapshot.py
    output) for the Next.js showcase site. The site bakes this in at
    build time too (so first load is instant with zero API calls),
    but exposing it live lets the site re-fetch fresh data without a
    full redeploy, and is useful for manual checking after a redeploy.
  - GET /recommend — the one genuinely live, personalized endpoint
    (mounted from recommendations/api.py's router).
  - GET /health — liveness check.

Run with:
    uvicorn api.main:app --reload
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from recommendations.api import init_state, router as recommendations_router

SNAPSHOT_PATH = Path(__file__).parent.parent / "site" / "data" / "snapshot.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_state()  # trains the recommendation models once at startup
    yield


app = FastAPI(title="Fan Engagement Platform API", lifespan=lifespan)

# Wide open for a public read-only showcase API — there's no auth or
# write path here, just precomputed metrics and a recommendation demo,
# so CORS doesn't need to be locked to a specific origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(recommendations_router)


@app.get("/snapshot")
def get_snapshot():
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)


@app.get("/health")
def health():
    return {"status": "ok"}
