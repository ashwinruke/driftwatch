import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from driftwatch.analyzers.documentation import (
    draft_update,
    find_stale_sections,
    format_drift_comment,
    index_specific_files,
)
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token
from driftwatch.github.comments import post_pr_comment
from driftwatch.retry import with_retry
from driftwatch.review.context import extract_changed_chunks
from driftwatch.review.orchestrator import review_pull_request

logger = logging.getLogger("driftwatch")

router = APIRouter()


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Verifies the signature and dispatches, then returns immediately.
    GitHub's webhook delivery has a hard timeout (~10s); the actual review
    -- token exchange, GitHub API calls, Semgrep/Bandit subprocesses,
    Gemini calls -- can easily take longer than that, so it runs as a
    background task after the response is sent rather than inline."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature, config.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    payload = json.loads(body)

    if event == "pull_request":
        action = payload.get("action")
        if action == "closed" and payload["pull_request"].get("merged"):
            background_tasks.add_task(_handle_pr_merged, payload)
        elif action in {"opened", "synchronize", "reopened"}:
            background_tasks.add_task(review_pull_request, payload)
        else:
            logger.info(f"Ignored pull_request action: {action}")
    elif event == "push":
        background_tasks.add_task(_handle_push, payload)
    else:
        logger.info(f"Ignored event: {event} / action: {payload.get('action')}")

    return {"status": "received"}


def _handle_pr_merged(payload: dict):
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    repo_full = payload["repository"]["full_name"]
    logger.info(f"Merged PR #{pr['number']} in {repo_full}: {pr['title']}")

    try:
        token = get_installation_token(config.GITHUB_APP_ID, config.GITHUB_INSTALLATION_ID)
        chunks = extract_changed_chunks(owner, repo, pr["number"], token)

        if not chunks:
            logger.info(f"No relevant code changes found in PR #{pr['number']} (no .py files changed, or no function/class-level changes detected)")

        comments_posted = 0

        for chunk in chunks:
            if comments_posted >= config.MAX_COMMENTS_PER_PR:
                logger.info(f"Reached comment cap ({config.MAX_COMMENTS_PER_PR}) for PR #{pr['number']}, skipping remaining chunks")
                break

            logger.info(f"Changed {chunk['type']} '{chunk['name']}' in {chunk['file']} (lines {chunk['start_line']}-{chunk['end_line']})")
            stale_sections = find_stale_sections(repo_full, chunk)

            for section in stale_sections:
                if comments_posted >= config.MAX_COMMENTS_PER_PR:
                    break

                logger.info(f"  -> Checking drift for '{section['heading']}' ({section['file_path']}) score={section['similarity']}")
                result = with_retry(draft_update, chunk, section)
                logger.info(f"     Verdict: {result['verdict']} | {result['reason']}")

                if result["verdict"] == "OUTDATED":
                    comment_body = format_drift_comment(chunk, section, result)
                    with_retry(post_pr_comment, owner, repo, pr["number"], token, comment_body)
                    comments_posted += 1
                    logger.info(f"     Posted PR comment for '{section['heading']}' ({comments_posted}/{config.MAX_COMMENTS_PER_PR})")

    except Exception:
        logger.exception(f"Failed processing PR #{pr['number']}")


def _handle_push(payload: dict):
    ref = payload.get("ref", "")
    repo_full = payload["repository"]["full_name"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    default_branch = payload["repository"]["default_branch"]

    if ref != f"refs/heads/{default_branch}":
        logger.info(f"Ignored push to non-default branch: {ref}")
        return

    added_or_modified = set()
    removed = set()

    for commit in payload.get("commits", []):
        for path in commit.get("added", []) + commit.get("modified", []):
            if path.endswith(".md"):
                added_or_modified.add(path)
        for path in commit.get("removed", []):
            if path.endswith(".md"):
                removed.add(path)

    # A file could appear in both lists across different commits in the same push;
    # if it was ultimately removed, treat it as removed, not modified.
    added_or_modified -= removed

    if not added_or_modified and not removed:
        logger.info(f"Push to {repo_full} touched no markdown files, skipping re-index")
        return

    logger.info(f"Push to {repo_full}: {len(added_or_modified)} doc file(s) changed, {len(removed)} removed")

    try:
        token = get_installation_token(config.GITHUB_APP_ID, config.GITHUB_INSTALLATION_ID)
        with_retry(index_specific_files, owner, repo, token, list(added_or_modified), list(removed))
    except Exception:
        logger.exception(f"Failed to re-index docs for {repo_full} after push")
