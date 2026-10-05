import logging
import sys

from driftwatch.analyzers.documentation import index_repo_docs
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token

logging.basicConfig(level=logging.INFO)

# Usage: python index_now.py <owner> <repo>
# Manual full rebuild. Repos are normally indexed automatically on first
# merged PR or app install (see github/webhooks.py) -- use this to force a
# rebuild.
owner, repo = sys.argv[1], sys.argv[2]

token = get_installation_token(
    config.GITHUB_APP_ID,
    config.GITHUB_INSTALLATION_ID,
)

index_repo_docs(owner, repo, token)
