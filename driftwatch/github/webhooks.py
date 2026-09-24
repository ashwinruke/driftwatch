import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from driftwatch.analyzers.documentation import analyze_chunk, index_specific_files
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token
from driftwatch.github.comments import post_pr_comment
from driftwatch.reporting.comment_formatter import format_finding_comment
from driftwatch.reporting.pr_summary import format_pr_summary
from driftwatch.retry import with_retry
from driftwatch.review import decision
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
    """Documentation-drift review for a merged PR. Shares the CandidateFinding
    schema, decision.decide() (validation + dedup), and the reporting
    formatters with the security pipeline (review.orchestrator) -- see
    analyzers.documentation.engine and validation.validator.validate_documentation
    for how a documentation finding fits schema built for code findings."""
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    repo_full = payload["repository"]["full_name"]
    pr_number = pr["number"]
    logger.info(f"Merged PR #{pr_number} in {repo_full}: {pr['title']}")

    try:
        token = get_installation_token(config.GITHUB_APP_ID, config.GITHUB_INSTALLATION_ID)
        chunks = extract_changed_chunks(owner, repo, pr_number, token)

        if not chunks:
            logger.info(f"No relevant code changes found in PR #{pr_number} (no .py files changed, or no function/class-level changes detected)")

        candidates: list[tuple] = []
        for chunk in chunks:
            logger.info(f"Changed {chunk['type']} '{chunk['name']}' in {chunk['file']} (lines {chunk['start_line']}-{chunk['end_line']})")
            candidates.extend(analyze_chunk(chunk, repo_full))

        decided = decision.decide(candidates, repo_full, pr_number)

        posted_findings = []
        for finding, _ in decided:
            if finding.validation_status != "accepted":
                logger.info(f"Not posting '{finding.title}': {finding.validation_status} (score={finding.validation_score})")
                continue
            if len(posted_findings) >= config.MAX_COMMENTS_PER_PR:
                logger.info(f"Reached comment cap ({config.MAX_COMMENTS_PER_PR}) for PR #{pr_number}, skipping remaining findings")
                break

            comment_body = format_finding_comment(finding)
            with_retry(post_pr_comment, owner, repo, pr_number, token, comment_body)
            posted_findings.append(finding)
            logger.info(f"Posted comment for '{finding.title}' ({len(posted_findings)}/{config.MAX_COMMENTS_PER_PR})")

        if candidates:
            candidate_findings = [candidate for candidate, _ in candidates]
            all_decided_findings = [finding for finding, _ in decided]
            summary = format_pr_summary(len(chunks), candidate_findings, all_decided_findings, posted_findings)
            with_retry(post_pr_comment, owner, repo, pr_number, token, summary)

    except Exception:
        logger.exception(f"Failed processing PR #{pr_number}")


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
