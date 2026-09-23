import logging

from driftwatch.analyzers import security
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token
from driftwatch.github.comments import post_pr_comment, post_review_comment
from driftwatch.llm.provider import GeminiProvider
from driftwatch.reporting.comment_formatter import format_finding_comment
from driftwatch.reporting.pr_summary import format_pr_summary
from driftwatch.retry import with_retry
from driftwatch.review import decision
from driftwatch.review.context import extract_changed_chunks

logger = logging.getLogger("driftwatch")

_provider = GeminiProvider()


def review_pull_request(payload: dict):
    """Security review for an opened/synchronize/reopened PR. Separate from
    (and untouched by) doc-drift's merge-triggered pipeline."""
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    repo_full = payload["repository"]["full_name"]
    pr_number = pr["number"]
    head_sha = pr["head"]["sha"]

    logger.info(f"Reviewing PR #{pr_number} in {repo_full} ({pr['title']!r}, action={payload.get('action')})")

    try:
        token = get_installation_token(config.GITHUB_APP_ID, config.GITHUB_INSTALLATION_ID)
        chunks = extract_changed_chunks(owner, repo, pr_number, token, include_module_level=True)

        candidates: list[tuple] = []
        for chunk in chunks:
            findings = security.analyze(chunk, repo_full, pr["title"], pr.get("body") or "", _provider)
            candidates.extend((finding, chunk) for finding in findings)

        decided = decision.decide(candidates, repo_full, pr_number)

        posted_findings = []
        for finding, chunk in decided:
            if len(posted_findings) >= config.MAX_COMMENTS_PER_PR:
                logger.info(f"Reached comment cap ({config.MAX_COMMENTS_PER_PR}) for PR #{pr_number}, skipping remaining findings")
                break

            comment_body = format_finding_comment(finding)
            with_retry(
                post_review_comment,
                owner, repo, pr_number, token, head_sha, finding.file_path, chunk["anchor_line"], comment_body,
            )
            posted_findings.append(finding)
            logger.info(f"Posted inline finding '{finding.title}' in {finding.file_path}:{chunk['anchor_line']} ({len(posted_findings)}/{config.MAX_COMMENTS_PER_PR})")

        candidate_findings = [candidate for candidate, _ in candidates]
        summary = format_pr_summary(len(chunks), candidate_findings, posted_findings)
        with_retry(post_pr_comment, owner, repo, pr_number, token, summary)

    except Exception:
        logger.exception(f"Failed reviewing PR #{pr_number}")
