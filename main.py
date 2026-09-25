# main.py
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from driftwatch.app import config
from driftwatch.dashboard.api import router as dashboard_router
from driftwatch.github.webhooks import router as github_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(github_router)
app.include_router(dashboard_router)

# The dashboard (Phase 6, a separate Next.js app) calls this API from a
# different origin. Read-only endpoints, no auth yet (MVP -- see
# docs/roadmap.md's Phase 6 report), so this is scoped to the dashboard's
# own origin rather than left wide open.
if config.DASHBOARD_ORIGIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.DASHBOARD_ORIGIN],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
