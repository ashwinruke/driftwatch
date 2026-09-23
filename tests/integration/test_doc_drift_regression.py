"""Confirms the Phase 1 changes to webhooks.py didn't disturb the existing
merge-triggered doc-drift pipeline."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

import driftwatch.github.webhooks as webhooks
from main import app

client = TestClient(app)

WEBHOOK_SECRET = "test-webhook-secret"


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_merged_pr_still_routes_to_doc_drift_handler(monkeypatch):
    calls = []
    monkeypatch.setattr(webhooks, "_handle_pr_merged", lambda payload: calls.append(payload))

    payload = {
        "action": "closed",
        "pull_request": {"number": 7, "title": "t", "merged": True},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }
    body = json.dumps(payload).encode()

    resp = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 200
    assert len(calls) == 1


def test_opened_pr_does_not_route_to_doc_drift_handler(monkeypatch):
    doc_drift_calls = []
    security_calls = []
    monkeypatch.setattr(webhooks, "_handle_pr_merged", lambda payload: doc_drift_calls.append(payload))
    monkeypatch.setattr(webhooks, "review_pull_request", lambda payload: security_calls.append(payload))

    payload = {
        "action": "opened",
        "pull_request": {"number": 7, "title": "t", "merged": False},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }
    body = json.dumps(payload).encode()

    resp = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 200
    assert doc_drift_calls == []
    assert len(security_calls) == 1
