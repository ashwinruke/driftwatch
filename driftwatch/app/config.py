import os

from dotenv import load_dotenv

load_dotenv()

GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
GITHUB_INSTALLATION_ID = os.environ["GITHUB_INSTALLATION_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
# Optional: falls back to Groq (OpenAI-compatible API) when set, since
# Gemini can return 503s under high demand. Fallback is simply not wired
# in if this isn't set -- see driftwatch/review/orchestrator.py.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_COMMENTS_PER_PR = int(os.environ.get("MAX_COMMENTS_PER_PR", "3"))
VALIDATION_ACCEPT_THRESHOLD = float(os.environ.get("VALIDATION_ACCEPT_THRESHOLD", "0.75"))
VALIDATION_REVIEW_THRESHOLD = float(os.environ.get("VALIDATION_REVIEW_THRESHOLD", "0.50"))
