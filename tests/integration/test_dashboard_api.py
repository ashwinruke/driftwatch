"""Dashboard read API tests (spec §59). Monkeypatches driftwatch.dashboard.
queries -- same "mock at the boundary" pattern as everywhere else in this
suite -- so these never attempt a real Postgres connection; they verify
response shape/status codes, not SQL correctness (that's covered by the
manual verification against local Postgres, per docs/roadmap.md's Phase 6
report)."""

from datetime import datetime

from fastapi.testclient import TestClient

import driftwatch.dashboard.queries as queries
from main import app

client = TestClient(app)


def test_overview_returns_shaped_response(monkeypatch):
    monkeypatch.setattr(queries, "get_overview", lambda: {
        "total_repositories": 2, "total_review_runs": 5, "total_prs_reviewed": 4,
        "total_findings": 10, "accepted_findings": 6, "rejected_findings": 3,
        "needs_review_findings": 1, "validation_acceptance_rate": 0.6,
        "average_review_latency_seconds": 12.5,
        "findings_by_category": {"security": 8, "documentation": 2},
        "findings_by_severity": {"high": 4, "low": 6},
    })

    resp = client.get("/api/v1/dashboard/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_repositories"] == 2
    assert body["findings_by_category"] == {"security": 8, "documentation": 2}


def test_list_repositories_returns_shaped_response(monkeypatch):
    monkeypatch.setattr(queries, "list_repositories", lambda: [{
        "id": 1, "full_name": "o/r", "default_branch": "main",
        "review_count": 3, "findings_count": 5,
        "validation_acceptance_rate": 0.8, "last_review": datetime(2026, 9, 25, 12, 0, 0),
    }])

    resp = client.get("/api/v1/repositories")

    assert resp.status_code == 200
    assert resp.json() == [{
        "id": 1, "full_name": "o/r", "default_branch": "main",
        "review_count": 3, "findings_count": 5,
        "validation_acceptance_rate": 0.8, "last_review": "2026-09-25T12:00:00",
    }]


def test_repository_detail_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(queries, "get_repository_detail", lambda repository_id: None)

    resp = client.get("/api/v1/repositories/999")

    assert resp.status_code == 404


def test_repository_detail_returns_shaped_response(monkeypatch):
    monkeypatch.setattr(queries, "get_repository_detail", lambda repository_id: {
        "id": 1, "full_name": "o/r", "default_branch": "main",
        "total_reviews": 3, "total_findings": 5, "last_review": datetime(2026, 9, 25, 12, 0, 0),
        "recent_reviews": [{
            "id": 10, "pr_number": 42, "pr_title": "t", "pr_author": "a",
            "run_type": "security", "status": "completed",
            "started_at": datetime(2026, 9, 25, 12, 0, 0), "completed_at": datetime(2026, 9, 25, 12, 0, 10),
        }],
    })

    resp = client.get("/api/v1/repositories/1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reviews"] == 3
    assert len(body["recent_reviews"]) == 1
    assert body["recent_reviews"][0]["pr_number"] == 42


def test_review_detail_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(queries, "get_review_detail", lambda review_run_id: None)

    resp = client.get("/api/v1/reviews/999")

    assert resp.status_code == 404


def test_review_detail_returns_shaped_response(monkeypatch):
    monkeypatch.setattr(queries, "get_review_detail", lambda review_run_id: {
        "id": 10, "repository_id": 1, "repository_full_name": "o/r",
        "pr_number": 42, "pr_title": "t", "pr_author": "a", "head_sha": "sha",
        "run_type": "security", "status": "completed", "error_message": None,
        "started_at": datetime(2026, 9, 25, 12, 0, 0), "completed_at": datetime(2026, 9, 25, 12, 0, 10),
        "files_analyzed": 2, "candidate_findings": 1, "accepted": 1, "rejected": 0, "needs_review": 0,
        "comments_posted": 1,
        "findings": [{
            "id": "f1", "category": "security", "severity": "high", "file_path": "app.py",
            "start_line": 1, "end_line": 2, "title": "SQL injection",
            "validation_status": "accepted", "validation_score": 0.9, "static_corroborated": True,
        }],
    })

    resp = client.get("/api/v1/reviews/10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["stats"]["files_analyzed"] == 2
    assert body["findings"][0]["title"] == "SQL injection"


def test_finding_detail_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(queries, "get_finding_detail", lambda finding_id: None)

    resp = client.get("/api/v1/findings/nonexistent")

    assert resp.status_code == 404


def test_finding_detail_returns_validation_breakdown_when_present(monkeypatch):
    monkeypatch.setattr(queries, "get_finding_detail", lambda finding_id: {
        "id": "f1", "review_run_id": 10, "category": "security", "severity": "high",
        "file_path": "app.py", "start_line": 1, "end_line": 2, "title": "SQL injection",
        "description": "d", "suggested_fix": "use params", "validation_status": "accepted",
        "validation_score": 0.985, "llm_confidence": 0.9, "validation_reasons": ["Location falls within the analyzed chunk"],
        "evidence": [{"source": "bandit", "description": "match", "file_path": "app.py", "start_line": 1, "end_line": None, "rule_id": "B608"}],
        "validation_result": {
            "diff_evidence_score": 1.0, "static_corroboration_score": 1.0,
            "ast_consistency_score": 1.0, "llm_confidence_score": 0.9, "final_score": 0.985,
        },
        "comment": {"comment_type": "finding", "github_comment_id": 111, "github_url": "https://github.com/x", "posted_at": datetime(2026, 9, 25, 12, 0, 0)},
    })

    resp = client.get("/api/v1/findings/f1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["validation_breakdown"]["final_score"] == 0.985
    assert body["comment"]["github_url"] == "https://github.com/x"


def test_finding_detail_has_no_breakdown_for_documentation_pass_through(monkeypatch):
    # validate_documentation() leaves all four component scores None --
    # the API must return validation_breakdown=None, not four nulls
    # dressed up as a breakdown.
    monkeypatch.setattr(queries, "get_finding_detail", lambda finding_id: {
        "id": "f2", "review_run_id": 11, "category": "documentation", "severity": "info",
        "file_path": "README.md", "start_line": 1, "end_line": 1, "title": "Usage",
        "description": "d", "suggested_fix": None, "validation_status": "accepted",
        "validation_score": 0.83, "llm_confidence": 0.83, "validation_reasons": [],
        "evidence": [],
        "validation_result": {
            "diff_evidence_score": None, "static_corroboration_score": None,
            "ast_consistency_score": None, "llm_confidence_score": None, "final_score": 0.83,
        },
        "comment": None,
    })

    resp = client.get("/api/v1/findings/f2")

    assert resp.status_code == 200
    assert resp.json()["validation_breakdown"] is None
