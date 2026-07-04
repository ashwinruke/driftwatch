import logging
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
load_dotenv()

from github_auth import get_installation_token
from doc_indexer import index_repo_docs

token = get_installation_token(
    os.environ["GITHUB_APP_ID"],
    os.environ["GITHUB_PRIVATE_KEY_PATH"],
    os.environ["GITHUB_INSTALLATION_ID"],
)

index_repo_docs("ashwin-bot", "Multithreaded_Web_Server", token)