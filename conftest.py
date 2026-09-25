import os

# Dummy values for the required env vars driftwatch.app.config reads at
# import time, so importing any driftwatch module under test doesn't require
# a real .env file. The presence of this file at the repo root also makes
# pytest add the repo root to sys.path, so `import driftwatch...` resolves
# without an editable install.
os.environ.setdefault("GITHUB_APP_ID", "test-app-id")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GITHUB_INSTALLATION_ID", "test-installation-id")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

# Force Langfuse tracing off during tests, even if the developer's local
# .env has real Langfuse credentials configured -- otherwise every local
# pytest run would silently send real trace data (from the integration
# tests exercising @traced_span/@traced_generation-wrapped production
# code) to that live Langfuse project. python-dotenv's load_dotenv()
# (driftwatch.app.config) doesn't override an env var that's already set,
# so setting this (not just leaving it unset) is what actually wins.
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
