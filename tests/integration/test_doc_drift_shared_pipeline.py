"""Confirms doc-drift now flows through the shared CandidateFinding /
decision.decide() / format_finding_comment() pipeline (Phase 4), mirroring
the pattern in test_security_review_flow.py -- GitHub/LLM calls mocked at
the driftwatch.github.webhooks module boundary."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

import driftwatch.github.webhooks as webhooks
from driftwatch.review.models import CandidateFinding
from main import app

client = TestClient(app)

WEBHOOK_SECRET = "test-webhook-secret"


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _post_merged_pr(pr_number: int):
    payload = {
        "action": "closed",
        "pull_request": {"number": pr_number, "title": "Change run_query signature", "merged": True},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }
    body = json.dumps(payload).encode()
    return client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )


def test_merged_pr_with_stale_doc_posts_shared_format_comment_and_summary(monkeypatch):
    posted_comments = []

    monkeypatch.setattr(webhooks, "get_installation_token", lambda app_id, installation_id: "fake-token")

    chunk = {
        "name": "run_query", "type": "function_definition", "start_line": 10,
        "end_line": 12, "text": "def run_query(user_id): ...", "file": "app.py",
    }
    monkeypatch.setattr(webhooks, "extract_changed_chunks", lambda *a, **k: [chunk])

    def fake_analyze_chunk(chunk, repository):
        candidate = CandidateFinding(
            category="documentation", severity="info", file_path="README.md",
            start_line=1, end_line=1, title="Usage",
            description="run_query now requires a user_id parameter.",
            reasoning_summary="run_query now requires a user_id parameter.",
            suggested_fix="Call run_query(user_id).", confidence=0.85,
        )
        return [(candidate, chunk)]

    monkeypatch.setattr(webhooks, "analyze_chunk", fake_analyze_chunk)
    monkeypatch.setattr(webhooks, "post_pr_comment", lambda owner, repo, pr_number, token, body: posted_comments.append(body))

    resp = _post_merged_pr(20)

    assert resp.status_code == 200
    assert len(posted_comments) == 2  # one finding comment + one PR summary
    finding_comment, summary_comment = posted_comments
    assert "Documentation: Usage" in finding_comment
    assert "Status: `accepted`" in finding_comment
    assert "Call run_query(user_id)." in finding_comment
    assert "Validated findings: 1" in summary_comment


def test_no_outdated_sections_posts_no_comments(monkeypatch):
    posted_comments = []
    monkeypatch.setattr(webhooks, "get_installation_token", lambda app_id, installation_id: "fake-token")
    monkeypatch.setattr(webhooks, "extract_changed_chunks", lambda *a, **k: [{
        "name": "f", "type": "function_definition", "start_line": 1, "end_line": 2,
        "text": "def f(): pass", "file": "app.py",
    }])
    monkeypatch.setattr(webhooks, "analyze_chunk", lambda chunk, repository: [])
    monkeypatch.setattr(webhooks, "post_pr_comment", lambda owner, repo, pr_number, token, body: posted_comments.append(body))

    resp = _post_merged_pr(21)

    assert resp.status_code == 200
    assert posted_comments == []


def test_two_stale_sections_with_same_heading_are_deduplicated(monkeypatch):
    # Two different code chunks both flag the same doc heading as stale --
    # should collapse to one posted comment, not two.
    posted_comments = []
    monkeypatch.setattr(webhooks, "get_installation_token", lambda app_id, installation_id: "fake-token")

    chunk_a = {"name": "a", "type": "function_definition", "start_line": 1, "end_line": 2, "text": "def a(): ...", "file": "app.py"}
    chunk_b = {"name": "b", "type": "function_definition", "start_line": 5, "end_line": 6, "text": "def b(): ...", "file": "app.py"}
    monkeypatch.setattr(webhooks, "extract_changed_chunks", lambda *a, **k: [chunk_a, chunk_b])

    def fake_analyze_chunk(chunk, repository):
        candidate = CandidateFinding(
            category="documentation", severity="info", file_path="README.md",
            start_line=1, end_line=1, title="Usage",
            description="stale", reasoning_summary="stale", confidence=0.7,
        )
        return [(candidate, chunk)]

    monkeypatch.setattr(webhooks, "analyze_chunk", fake_analyze_chunk)
    monkeypatch.setattr(webhooks, "post_pr_comment", lambda owner, repo, pr_number, token, body: posted_comments.append(body))

    resp = _post_merged_pr(22)

    assert resp.status_code == 200
    assert len(posted_comments) == 2  # one deduplicated finding comment + summary
