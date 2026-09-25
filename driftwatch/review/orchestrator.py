import logging

from driftwatch.analyzers.security import SecurityEngine
from driftwatch.app import config
from driftwatch.github.auth import get_installation_token
from driftwatch.github.comments import post_pr_comment, post_review_comment
from driftwatch.llm.provider import FallbackProvider, GeminiProvider, GroqProvider
from driftwatch.observability.tracing import tag_current_run, traced_span
from driftwatch.reporting.comment_formatter import format_finding_comment
from driftwatch.reporting.pr_summary import format_pr_summary
from driftwatch.retry import with_retry
from driftwatch.review import decision
from driftwatch.review.context import extract_changed_chunks
from driftwatch.review.engine import ReviewContext
from driftwatch.static_analysis.runner import run_static_analysis

logger = logging.getLogger("driftwatch")

# Falls back to Groq if GROQ_API_KEY is configured (Gemini can return 503s
# under high demand); otherwise Gemini alone, matching pre-fallback behavior.
_provider = FallbackProvider(GeminiProvider(), GroqProvider()) if config.GROQ_API_KEY else GeminiProvider()

# The engines that run over PR-opened/synchronize/reopened chunks. Just
# security for now -- bug/quality engines get added here the same way
# once they exist, with no other change needed in analyze_and_decide.
_ENGINES = [SecurityEngine(_provider)]


def analyze_and_decide(chunks: list[dict], repository: str, pr_title: str, pr_body: str, pr_number: int):
    """Runs every engine in _ENGINES over every chunk, then validates the
    results. Shared by the live webhook path (review_pull_request) and
    driftwatch.cli.evaluate, so evaluation measures the exact same code
    path production uses -- callers are responsible for having already run
    static analysis on the chunks (chunk["static_matches"]) beforehand."""
    candidates: list[tuple] = []
    for chunk in chunks:
        context = ReviewContext(chunk=chunk, repository=repository, pull_request=pr_number, pr_title=pr_title, pr_body=pr_body)
        for engine in _ENGINES:
            findings = engine.analyze(context)
            candidates.extend((finding, chunk) for finding in findings)

    decided = decision.decide(candidates, repository, pr_number)
    return candidates, decided


@traced_span("review-pull-request")
def review_pull_request(payload: dict):
    """Security review for an opened/synchronize/reopened PR. Separate from
    (and untouched by) doc-drift's merge-triggered pipeline."""
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    repo_full = payload["repository"]["full_name"]
    pr_number = pr["number"]
    head_sha = pr["head"]["sha"]

    tag_current_run(repository=repo_full, pull_request=pr_number)
    logger.info(f"Reviewing PR #{pr_number} in {repo_full} ({pr['title']!r}, action={payload.get('action')})")

    try:
        token = get_installation_token(config.GITHUB_APP_ID, config.GITHUB_INSTALLATION_ID)
        chunks = extract_changed_chunks(owner, repo, pr_number, token, include_module_level=True)
        run_static_analysis(chunks)  # attaches chunk["static_matches"] in place, once for the whole PR

        candidates, decided = analyze_and_decide(chunks, repo_full, pr["title"], pr.get("body") or "", pr_number)

        # Only "accepted" findings get posted (spec §19's publish rule).
        # "needs_review"/"rejected" are logged for visibility but not
        # persisted anywhere yet -- no review_runs/findings schema exists.
        accepted = [(finding, chunk) for finding, chunk in decided if finding.validation_status == "accepted"]
        for finding, _ in decided:
            if finding.validation_status != "accepted":
                logger.info(f"Not posting '{finding.title}': {finding.validation_status} (score={finding.validation_score})")

        posted_findings = []
        for finding, chunk in accepted:
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
        all_decided_findings = [finding for finding, _ in decided]
        summary = format_pr_summary(len(chunks), candidate_findings, all_decided_findings, posted_findings)
        with_retry(post_pr_comment, owner, repo, pr_number, token, summary)

    except Exception:
        logger.exception(f"Failed reviewing PR #{pr_number}")
