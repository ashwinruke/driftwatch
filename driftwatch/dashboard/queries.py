"""Read-only, parameterized SQL against the tables driftwatch/persistence/
review_store.py writes. Returns plain dicts (via RealDictCursor), not
Pydantic models -- driftwatch/dashboard/api.py shapes those from these
rows, keeping "what's in the database" separate from "what the API
promises to return" (spec §59)."""

from psycopg2.extras import RealDictCursor

from driftwatch.persistence.db import get_connection


def _dict_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def get_overview() -> dict:
    conn = get_connection()
    cur = _dict_cursor(conn)

    cur.execute("SELECT COUNT(*) AS n FROM repositories")
    total_repositories = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM review_runs")
    total_review_runs = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(DISTINCT (repository_id, pr_number)) AS n FROM review_runs")
    total_prs_reviewed = cur.fetchone()["n"]

    cur.execute("SELECT validation_status, COUNT(*) AS n FROM findings GROUP BY validation_status")
    status_counts = {row["validation_status"]: row["n"] for row in cur.fetchall()}

    cur.execute("SELECT category, COUNT(*) AS n FROM findings GROUP BY category")
    findings_by_category = {row["category"]: row["n"] for row in cur.fetchall()}

    cur.execute("SELECT severity, COUNT(*) AS n FROM findings GROUP BY severity")
    findings_by_severity = {row["severity"]: row["n"] for row in cur.fetchall()}

    cur.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_latency
        FROM review_runs WHERE completed_at IS NOT NULL
    """)
    average_review_latency_seconds = cur.fetchone()["avg_latency"]

    cur.close()
    conn.close()

    total_findings = sum(status_counts.values())
    accepted = status_counts.get("accepted", 0)
    return {
        "total_repositories": total_repositories,
        "total_review_runs": total_review_runs,
        "total_prs_reviewed": total_prs_reviewed,
        "total_findings": total_findings,
        "accepted_findings": accepted,
        "rejected_findings": status_counts.get("rejected", 0),
        "needs_review_findings": status_counts.get("needs_review", 0),
        "validation_acceptance_rate": (accepted / total_findings) if total_findings else None,
        "average_review_latency_seconds": float(average_review_latency_seconds) if average_review_latency_seconds is not None else None,
        "findings_by_category": findings_by_category,
        "findings_by_severity": findings_by_severity,
    }


def list_repositories() -> list[dict]:
    conn = get_connection()
    cur = _dict_cursor(conn)
    cur.execute("""
        SELECT
            r.id, r.full_name, r.default_branch,
            COUNT(DISTINCT rr.id) AS review_count,
            COUNT(f.id) AS findings_count,
            COUNT(f.id) FILTER (WHERE f.validation_status = 'accepted') AS accepted_count,
            MAX(rr.started_at) AS last_review
        FROM repositories r
        LEFT JOIN review_runs rr ON rr.repository_id = r.id
        LEFT JOIN findings f ON f.review_run_id = rr.id
        GROUP BY r.id, r.full_name, r.default_branch
        ORDER BY r.full_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for row in rows:
        row["validation_acceptance_rate"] = (row["accepted_count"] / row["findings_count"]) if row["findings_count"] else None
    return rows


def get_repository_detail(repository_id: int, recent_limit: int = 10) -> dict | None:
    conn = get_connection()
    cur = _dict_cursor(conn)

    cur.execute("SELECT id, full_name, default_branch FROM repositories WHERE id = %s", (repository_id,))
    repo = cur.fetchone()
    if not repo:
        cur.close()
        conn.close()
        return None

    cur.execute("SELECT COUNT(*) AS n FROM review_runs WHERE repository_id = %s", (repository_id,))
    total_reviews = cur.fetchone()["n"]

    cur.execute(
        "SELECT COUNT(*) AS n FROM findings f JOIN review_runs rr ON rr.id = f.review_run_id WHERE rr.repository_id = %s",
        (repository_id,),
    )
    total_findings = cur.fetchone()["n"]

    cur.execute("SELECT MAX(started_at) AS last_review FROM review_runs WHERE repository_id = %s", (repository_id,))
    last_review = cur.fetchone()["last_review"]

    cur.execute(
        """
        SELECT id, pr_number, pr_title, pr_author, run_type, status, started_at, completed_at
        FROM review_runs WHERE repository_id = %s
        ORDER BY started_at DESC LIMIT %s
        """,
        (repository_id, recent_limit),
    )
    recent_reviews = cur.fetchall()

    cur.close()
    conn.close()
    return {
        **repo,
        "total_reviews": total_reviews,
        "total_findings": total_findings,
        "last_review": last_review,
        "recent_reviews": recent_reviews,
    }


def list_repository_reviews(repository_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    conn = get_connection()
    cur = _dict_cursor(conn)
    cur.execute(
        """
        SELECT id, pr_number, pr_title, pr_author, run_type, status, started_at, completed_at
        FROM review_runs WHERE repository_id = %s
        ORDER BY started_at DESC LIMIT %s OFFSET %s
        """,
        (repository_id, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_review_detail(review_run_id: int) -> dict | None:
    conn = get_connection()
    cur = _dict_cursor(conn)

    cur.execute(
        """
        SELECT rr.*, r.full_name AS repository_full_name
        FROM review_runs rr JOIN repositories r ON r.id = rr.repository_id
        WHERE rr.id = %s
        """,
        (review_run_id,),
    )
    run = cur.fetchone()
    if not run:
        cur.close()
        conn.close()
        return None

    cur.execute("SELECT COUNT(DISTINCT file_path) AS n FROM changed_chunks WHERE review_run_id = %s", (review_run_id,))
    files_analyzed = cur.fetchone()["n"]

    cur.execute(
        """
        SELECT f.id, f.category, f.severity, f.file_path, f.start_line, f.end_line,
               f.title, f.validation_status, f.validation_score,
               EXISTS (
                   SELECT 1 FROM evidence e WHERE e.finding_id = f.id AND e.source IN ('semgrep', 'bandit', 'gitleaks')
               ) AS static_corroborated
        FROM findings f WHERE f.review_run_id = %s
        ORDER BY f.validation_score DESC NULLS LAST
        """,
        (review_run_id,),
    )
    findings = cur.fetchall()

    cur.execute(
        "SELECT COUNT(*) AS n FROM comments WHERE review_run_id = %s AND comment_type = 'finding'",
        (review_run_id,),
    )
    comments_posted = cur.fetchone()["n"]

    cur.close()
    conn.close()

    status_counts = {"accepted": 0, "rejected": 0, "needs_review": 0}
    for f in findings:
        status_counts[f["validation_status"]] = status_counts.get(f["validation_status"], 0) + 1

    return {
        **run,
        "files_analyzed": files_analyzed,
        "candidate_findings": len(findings),
        "accepted": status_counts["accepted"],
        "rejected": status_counts["rejected"],
        "needs_review": status_counts["needs_review"],
        "comments_posted": comments_posted,
        "findings": findings,
    }


def get_finding_detail(finding_id: str) -> dict | None:
    conn = get_connection()
    cur = _dict_cursor(conn)

    cur.execute(
        """
        SELECT f.*, rr.repository_id
        FROM findings f JOIN review_runs rr ON rr.id = f.review_run_id
        WHERE f.id = %s
        """,
        (finding_id,),
    )
    finding = cur.fetchone()
    if not finding:
        cur.close()
        conn.close()
        return None

    cur.execute(
        "SELECT source, description, file_path, start_line, end_line, rule_id FROM evidence WHERE finding_id = %s",
        (finding_id,),
    )
    evidence = cur.fetchall()

    cur.execute(
        """
        SELECT diff_evidence_score, static_corroboration_score, ast_consistency_score,
               llm_confidence_score, final_score
        FROM validation_results WHERE finding_id = %s
        """,
        (finding_id,),
    )
    validation_result = cur.fetchone()

    cur.execute(
        "SELECT comment_type, github_comment_id, github_url, posted_at FROM comments WHERE finding_id = %s LIMIT 1",
        (finding_id,),
    )
    comment = cur.fetchone()

    cur.close()
    conn.close()
    return {
        **finding,
        "evidence": evidence,
        "validation_result": validation_result,
        "comment": comment,
    }
