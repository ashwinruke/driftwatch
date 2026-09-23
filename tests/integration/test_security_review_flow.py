import hashlib
import hmac
import json

from fastapi.testclient import TestClient

import driftwatch.review.orchestrator as orchestrator
from driftwatch.review.models import CandidateFinding
from main import app

client = TestClient(app)

WEBHOOK_SECRET = "test-webhook-secret"  # matches conftest.py's dummy env var


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _post_webhook(payload: dict):
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


def test_opened_pr_with_seeded_vulnerability_posts_inline_comment_and_summary(monkeypatch):
    """A finding with real static-analysis corroboration (Semgrep/Bandit
    genuinely run, not mocked) clears the validation threshold and gets
    posted -- letting the real static_analysis + validation stack run end
    to end here, mocked only at the GitHub/LLM boundary."""
    posted_review_comments = []
    posted_summaries = []

    monkeypatch.setattr(orchestrator, "get_installation_token", lambda app_id, installation_id: "fake-token")

    chunk = {
        "name": "run_query",
        "type": "function_definition",
        "start_line": 10,
        "end_line": 12,
        "text": 'def run_query(cursor, user_id):\n    query = f"SELECT * FROM users WHERE id = {user_id}"\n    cursor.execute(query)',
        "file": "app.py",
        "anchor_line": 11,
        "diff_ranges": [(11, 12)],
    }
    monkeypatch.setattr(orchestrator, "extract_changed_chunks", lambda *a, **k: [chunk])

    seeded_finding = CandidateFinding(
        category="security",
        severity="high",
        file_path="app.py",
        start_line=11,
        end_line=12,
        title="SQL injection",
        description="user_id is interpolated directly into the query string.",
        reasoning_summary="f-string builds SQL with unsanitized input.",
        suggested_fix="Use a parameterized query instead.",
        confidence=0.9,
    )
    monkeypatch.setattr(orchestrator._provider, "generate_findings", lambda prompt: [seeded_finding])

    monkeypatch.setattr(orchestrator, "post_review_comment", lambda *a, **k: posted_review_comments.append((a, k)))
    monkeypatch.setattr(orchestrator, "post_pr_comment", lambda *a, **k: posted_summaries.append((a, k)))

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Add user lookup endpoint",
            "body": "Adds a helper to look up a user by id.",
            "head": {"sha": "deadbeef"},
        },
        "repository": {
            "name": "demo-repo",
            "full_name": "ashwinruke/demo-repo",
            "owner": {"login": "ashwinruke"},
            "default_branch": "main",
        },
    }

    resp = _post_webhook(payload)

    assert resp.status_code == 200
    assert len(posted_review_comments) == 1
    assert "SQL injection" in posted_review_comments[0][0][-1]  # comment body is the last positional arg
    assert len(posted_summaries) == 1


def test_finding_without_corroboration_is_not_posted_but_would_have_been_in_phase_1(monkeypatch):
    """The concrete before/after-validation difference Phase 2 exists to
    produce: a high-confidence finding that would have cleared Phase 1's
    bare confidence floor, but has no static-analysis corroboration and no
    diff overlap, now correctly lands below the accept threshold."""
    posted_review_comments = []

    monkeypatch.setattr(orchestrator, "get_installation_token", lambda app_id, installation_id: "fake-token")
    monkeypatch.setattr(orchestrator, "extract_changed_chunks", lambda *a, **k: [{
        "name": "f", "type": "function_definition", "start_line": 1, "end_line": 2,
        "text": "def f():\n    return 1\n", "file": "app.py", "anchor_line": 1,
        "diff_ranges": [(1, 2)],
    }])

    # High confidence (would have passed Phase 1's SECURITY_MIN_CONFIDENCE
    # floor of 0.6), but nothing in the actual code supports it, and the
    # code is genuinely benign, so no static tool corroborates it either.
    unsupported_finding = CandidateFinding(
        category="security", severity="low", file_path="app.py",
        start_line=1, end_line=2, title="Maybe an issue",
        description="Possible issue in this function.",
        reasoning_summary="speculative", confidence=0.7,
    )
    monkeypatch.setattr(orchestrator._provider, "generate_findings", lambda prompt: [unsupported_finding])
    monkeypatch.setattr(orchestrator, "post_review_comment", lambda *a, **k: posted_review_comments.append((a, k)))
    monkeypatch.setattr(orchestrator, "post_pr_comment", lambda *a, **k: None)

    payload = {
        "action": "synchronize",
        "pull_request": {"number": 1, "title": "t", "body": "", "head": {"sha": "sha"}},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }

    resp = _post_webhook(payload)

    assert resp.status_code == 200
    assert posted_review_comments == []
