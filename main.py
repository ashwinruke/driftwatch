# main.py
from dotenv import load_dotenv
load_dotenv()

import hmac
import hashlib
import json
import logging
import os
from fastapi import FastAPI, Request, HTTPException

from github_auth import get_installation_token
from diff_extractor import extract_changed_chunks
from doc_indexer import index_repo_docs
from matcher import find_stale_sections
from drafter import draft_update
from pr_commenter import post_pr_comment, format_drift_comment


app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("driftwatch")

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
GITHUB_PRIVATE_KEY_PATH = os.environ["GITHUB_PRIVATE_KEY_PATH"]
GITHUB_INSTALLATION_ID = os.environ["GITHUB_INSTALLATION_ID"]

def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

@app.post("/webhook")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    payload = json.loads(body)

    if event == "pull_request" and payload.get("action") == "closed" and payload["pull_request"].get("merged"):
        pr = payload["pull_request"]
        owner = payload["repository"]["owner"]["login"]
        repo = payload["repository"]["name"]
        repo_full = payload["repository"]["full_name"]
        logger.info(f"Merged PR #{pr['number']} in {repo_full}: {pr['title']}")

        try:
            token = get_installation_token(GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH, GITHUB_INSTALLATION_ID)
            chunks = extract_changed_chunks(owner, repo, pr["number"], token)

            for chunk in chunks:
                logger.info(f"Changed {chunk['type']} '{chunk['name']}' in {chunk['file']} (lines {chunk['start_line']}-{chunk['end_line']})")
                stale_sections = find_stale_sections(repo_full, chunk)

                for section in stale_sections:
                    logger.info(f"  -> Checking drift for '{section['heading']}' ({section['file_path']}) score={section['similarity']}")
                    result = draft_update(chunk, section)
                    logger.info(f"     Verdict: {result['verdict']} | {result['reason']}")

                    if result["verdict"] == "OUTDATED":
                        comment_body = format_drift_comment(chunk, section, result)
                        post_pr_comment(owner, repo, pr["number"], token, comment_body)
                        logger.info(f"     Posted PR comment for '{section['heading']}'")

        except Exception:
            logger.exception(f"Failed processing PR #{pr['number']}")
    else:
        logger.info(f"Ignored event: {event} / action: {payload.get('action')}")

    return {"status": "received"}