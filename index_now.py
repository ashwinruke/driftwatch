import logging

from driftwatch.analyzers.documentation import index_repo_docs
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token

logging.basicConfig(level=logging.INFO)

token = get_installation_token(
    config.GITHUB_APP_ID,
    config.GITHUB_INSTALLATION_ID,
)

index_repo_docs("ashwinruke", "Multithreaded_Web_Server", token)
