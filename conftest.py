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
