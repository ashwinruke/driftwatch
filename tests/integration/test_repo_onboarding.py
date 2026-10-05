"""Repo onboarding: installing the App on a repo (or granting it access) queues
a doc index for that repo, and the first merged PR for a never-indexed repo
does too, ahead of doc-drift running. Mirrors test_doc_drift_regression.py's
boundary-mocking style -- no GitHub, Gemini, or Postgres calls."""

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


def _post(payload: dict, event: str):
    body = json.dumps(payload).encode()
    return client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": event,
            "Content-Type": "application/json",
        },
    )


def _stub_handlers(monkeypatch):
    indexed = []
    monkeypatch.setattr(webhooks, "_index_docs_if_needed", lambda full_name, installation_id: indexed.append(full_name))
    monkeypatch.setattr(webhooks, "_handle_pr_merged", lambda payload: None)
    monkeypatch.setattr(webhooks, "review_pull_request", lambda payload: None)
    return indexed


def test_installation_created_indexes_every_listed_repo(monkeypatch):
    indexed = _stub_handlers(monkeypatch)
    payload = {
        "action": "created",
        "installation": {"id": 1},
        "repositories": [{"full_name": "o/a"}, {"full_name": "o/b"}],
    }

    resp = _post(payload, "installation")

    assert resp.status_code == 200
    assert indexed == ["o/a", "o/b"]


def test_installation_repositories_added_indexes_only_added_repos(monkeypatch):
    indexed = _stub_handlers(monkeypatch)
    payload = {
        "action": "added",
        "installation": {"id": 1},
        "repositories_added": [{"full_name": "o/new"}],
        "repositories_removed": [{"full_name": "o/gone"}],
    }

    resp = _post(payload, "installation_repositories")

    assert resp.status_code == 200
    assert indexed == ["o/new"]


def test_installation_repositories_removed_does_not_index(monkeypatch):
    indexed = _stub_handlers(monkeypatch)
    payload = {
        "action": "removed",
        "installation": {"id": 1},
        "repositories_removed": [{"full_name": "o/gone"}],
    }

    resp = _post(payload, "installation_repositories")

    assert resp.status_code == 200
    assert indexed == []


def test_merged_pr_queues_docs_index_before_doc_drift(monkeypatch):
    order = []
    monkeypatch.setattr(webhooks, "_index_docs_if_needed", lambda full_name, installation_id: order.append(("index", full_name)))
    monkeypatch.setattr(webhooks, "_handle_pr_merged", lambda payload: order.append(("drift", payload["pull_request"]["number"])))

    payload = {
        "action": "closed",
        "pull_request": {"number": 9, "title": "t", "merged": True},
        "installation": {"id": 1},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }

    resp = _post(payload, "pull_request")

    assert resp.status_code == 200
    assert order == [("index", "o/r"), ("drift", 9)]


def test_opened_pr_does_not_queue_docs_index(monkeypatch):
    # Doc-drift only reads the index on merge, so opened PRs shouldn't embed anything.
    indexed = _stub_handlers(monkeypatch)
    payload = {
        "action": "opened",
        "pull_request": {"number": 3, "title": "t", "body": "", "head": {"sha": "s"}},
        "installation": {"id": 1},
        "repository": {"name": "r", "full_name": "o/r", "owner": {"login": "o"}, "default_branch": "main"},
    }

    resp = _post(payload, "pull_request")

    assert resp.status_code == 200
    assert indexed == []
