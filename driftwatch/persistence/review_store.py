"""Phase 6 (spec §28/§60, trimmed -- see docs/roadmap.md's Phase 6 report):
writes review-run data to the tables driftwatch/persistence/db.py's
setup_schema() adds, so the dashboard has something to read. Every
function opens and closes its own short-lived connection (matching the
existing style in analyzers/documentation/indexer.py) rather than holding
one open across an entire review, which can take many seconds of LLM
calls. Callers (review/orchestrator.py, github/webhooks.py) wrap these in
their own try/except -- a persistence failure must never block the
GitHub-facing review itself, the same resilience principle already applied
to static-analysis tool failures."""

import logging

from driftwatch.persistence.db import get_connection
from driftwatch.review.models import Finding

logger = logging.getLogger("driftwatch")


def safe_call(fn, *args, **kwargs):
    """Runs a persistence write, logging (never raising) on failure -- a DB
    outage must never block the GitHub-facing review itself. Callers that
    need a value back (e.g. a review_run_id for subsequent calls) get None
    on failure and should guard against that."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.exception(f"Persistence write failed: {fn.__name__}")
        return None


def get_or_create_repository(owner: str, name: str, default_branch: str | None = None) -> int:
    full_name = f"{owner}/{name}"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM repositories WHERE full_name = %s", (full_name,))
    row = cur.fetchone()
    if row:
        repository_id = row[0]
    else:
        cur.execute(
            "INSERT INTO repositories (full_name, owner, name, default_branch) VALUES (%s, %s, %s, %s) RETURNING id",
            (full_name, owner, name, default_branch),
        )
        repository_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return repository_id


def start_review_run(
    repository_id: int,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    head_sha: str | None,
    run_type: str,
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO review_runs (repository_id, pr_number, pr_title, pr_author, head_sha, run_type, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'running')
        RETURNING id
        """,
        (repository_id, pr_number, pr_title, pr_author, head_sha, run_type),
    )
    review_run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return review_run_id


def record_changed_chunks(review_run_id: int, chunks: list[dict]) -> None:
    if not chunks:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO changed_chunks (review_run_id, file_path, chunk_type, chunk_name, start_line, end_line)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            (review_run_id, c["file"], c.get("type"), c.get("name"), c.get("start_line"), c.get("end_line"))
            for c in chunks
        ],
    )
    conn.commit()
    cur.close()
    conn.close()


def record_findings(review_run_id: int, findings: list[Finding]) -> None:
    """Persists every decided finding (accepted, rejected, AND
    needs_review) -- the dashboard's findings table (spec §52) shows all
    three statuses, and this data already exists in `decided`, it's just
    thrown away today once the review completes."""
    if not findings:
        return
    conn = get_connection()
    cur = conn.cursor()

    for finding in findings:
        cur.execute(
            """
            INSERT INTO findings (
                id, review_run_id, category, severity, title, description,
                file_path, start_line, end_line, suggested_fix,
                llm_confidence, validation_score, validation_status, validation_reasons
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                finding.id, review_run_id, finding.category, finding.severity,
                finding.title, finding.description, finding.file_path,
                finding.start_line, finding.end_line, finding.suggested_fix,
                finding.llm_confidence, finding.validation_score,
                finding.validation_status, finding.validation_reasons,
            ),
        )

        if finding.evidence:
            cur.executemany(
                """
                INSERT INTO evidence (finding_id, source, description, file_path, start_line, end_line, rule_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (finding.id, e.source, e.description, e.file_path, e.start_line, e.end_line, e.rule_id)
                    for e in finding.evidence
                ],
            )

        components = finding.validation_components or {}
        cur.execute(
            """
            INSERT INTO validation_results (
                finding_id, diff_evidence_score, static_corroboration_score,
                ast_consistency_score, llm_confidence_score, final_score
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                finding.id,
                components.get("diff_evidence"),
                components.get("static_corroboration"),
                components.get("ast_consistency"),
                components.get("llm_confidence"),
                finding.validation_score,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def record_comment(review_run_id: int, finding_id: str | None, comment_type: str, github_response: dict) -> None:
    """`github_response` is the raw dict already returned by
    post_pr_comment/post_review_comment (driftwatch/github/comments.py) --
    its `id`/`html_url` were previously discarded after posting."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO comments (review_run_id, finding_id, comment_type, github_comment_id, github_url)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (review_run_id, finding_id, comment_type, github_response.get("id"), github_response.get("html_url")),
    )
    conn.commit()
    cur.close()
    conn.close()


def complete_review_run(review_run_id: int, status: str, error_message: str | None = None) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE review_runs SET status = %s, error_message = %s, completed_at = NOW() WHERE id = %s",
        (status, error_message, review_run_id),
    )
    conn.commit()
    cur.close()
    conn.close()
