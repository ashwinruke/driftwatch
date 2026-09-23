import os

from dotenv import load_dotenv

load_dotenv()

GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
GITHUB_INSTALLATION_ID = os.environ["GITHUB_INSTALLATION_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
MAX_COMMENTS_PER_PR = int(os.environ.get("MAX_COMMENTS_PER_PR", "3"))
SECURITY_MIN_CONFIDENCE = float(os.environ.get("SECURITY_MIN_CONFIDENCE", "0.6"))
