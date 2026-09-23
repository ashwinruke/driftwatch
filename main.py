# main.py
import logging

from fastapi import FastAPI

from driftwatch.github.webhooks import router as github_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(github_router)
