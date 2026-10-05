"""Round-trip tests against a real Postgres. Skipped unless RUN_DB_TESTS=1,
so the default `pytest tests/unit tests/integration` run never needs a
database. CI sets RUN_DB_TESTS=1 against a pgvector service container; run
locally with the same env vars (see CLAUDE.md's Commands section)."""

import os
import uuid

import pytest

from driftwatch.analyzers.documentation import indexer
from driftwatch.persistence import evaluation_store, review_store
from driftwatch.persistence.db import get_connection
from driftwatch.review.models import Evidence, Finding
from driftwatch.dashboard import queries

pytestmark = pytest.mark.skipif(os.environ.get("RUN_DB_TESTS") != "1", reason="set RUN_DB_TESTS=1 to run against a real database")


@pytest.fixture
def repo_name():
    owner = "ci-test"
    name = f"repo-{uuid.uuid4().hex[:10]}"
    yield owner, name
    _delete_repository(f"{owner}/{name}")


def _delete_repository(full_name: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM comments WHERE review_run_id IN (
            SELECT rr.id FROM review_runs rr JOIN repositories r ON r.id = rr.repository_id WHERE r.full_name = %s)
        """,
        (full_name,),
    )
    cur.execute(
        """
        DELETE FROM validation_results WHERE finding_id IN (
            SELECT f.id FROM findings f JOIN review_runs rr ON rr.id = f.review_run_id
            JOIN repositories r ON r.id = rr.repository_id WHERE r.full_name = %s)
        """,
        (full_name,),
    )
    cur.execute(
        """
        DELETE FROM evidence WHERE finding_id IN (
            SELECT f.id FROM findings f JOIN review_runs rr ON rr.id = f.review_run_id
            JOIN repositories r ON r.id = rr.repository_id WHERE r.full_name = %s)
        """,
        (full_name,),
    )
    cur.execute(
        """
        DELETE FROM findings WHERE review_run_id IN (
            SELECT rr.id FROM review_runs rr JOIN repositories r ON r.id = rr.repository_id WHERE r.full_name = %s)
        """,
        (full_name,),
    )
    cur.execute(
        "DELETE FROM changed_chunks WHERE review_run_id IN (SELECT rr.id FROM review_runs rr JOIN repositories r ON r.id = rr.repository_id WHERE r.full_name = %s)",
        (full_name,),
    )
    cur.execute(
        "DELETE FROM review_runs WHERE repository_id IN (SELECT id FROM repositories WHERE full_name = %s)",
        (full_name,),
    )
    cur.execute("DELETE FROM doc_sections WHERE repo = %s", (full_name,))
    cur.execute("DELETE FROM repositories WHERE full_name = %s", (full_name,))
    conn.commit()
    cur.close()
    conn.close()


def _finding(title: str) -> Finding:
    return Finding(
        id=str(uuid.uuid4()),
        category="security",
        severity="high",
        title=title,
        description="d",
        repository="ci-test/x",
        pull_request=1,
        file_path="app.py",
        start_line=11,
        end_line=12,
        changed_code="code",
        evidence=[Evidence(source="bandit", description="match", file_path="app.py", start_line=11, rule_id="B608")],
        llm_confidence=0.9,
        validation_score=0.98,
        validation_status="accepted",
        validation_reasons=["Location falls within the analyzed chunk"],
        validation_components={"diff_evidence": 1.0, "static_corroboration": 1.0, "ast_consistency": 1.0, "llm_confidence": 0.9},
    )


def test_review_run_round_trips_into_dashboard_queries(repo_name):
    owner, name = repo_name
    full_name = f"{owner}/{name}"

    repository_id = review_store.get_or_create_repository(owner, name)
    run_id = review_store.start_review_run(repository_id, 42, "Title", "author", "sha123", "security")
    review_store.record_changed_chunks(run_id, [{"file": "app.py", "type": "function_definition", "name": "f", "start_line": 10, "end_line": 12}])
    review_store.record_findings(run_id, [_finding("SQL injection")])
    review_store.record_comment(run_id, None, "summary", {"id": 9, "html_url": "https://example.test/9"})
    review_store.complete_review_run(run_id, "completed")

    detail = queries.get_review_detail(run_id)

    assert detail["repository_full_name"] == full_name
    assert detail["files_analyzed"] == 1
    assert detail["candidate_findings"] == 1
    assert detail["accepted"] == 1
    assert detail["findings"][0]["static_corroborated"] is True
    assert detail["status"] == "completed"


def test_idempotency_lookup_finds_completed_run_for_same_commit(repo_name):
    owner, name = repo_name
    full_name = f"{owner}/{name}"

    repository_id = review_store.get_or_create_repository(owner, name)
    run_id = review_store.start_review_run(repository_id, 7, "t", "a", "commit-abc", "security")
    review_store.complete_review_run(run_id, "completed")

    existing = review_store.find_existing_run(full_name, 7, "commit-abc", "security")

    assert review_store.should_skip_review(existing) is True
    assert review_store.find_existing_run(full_name, 7, "other-commit", "security") is None


def test_doc_index_is_stamped_once_and_skipped_afterwards(repo_name, monkeypatch):
    owner, name = repo_name
    full_name = f"{owner}/{name}"
    listed = []
    monkeypatch.setattr(indexer, "fetch_markdown_files", lambda *a, **k: listed.append(a) or [])

    indexer.index_repo_docs(owner, name, "tok", only_if_unindexed=True)
    indexer.index_repo_docs(owner, name, "tok", only_if_unindexed=True)

    assert len(listed) == 1
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT docs_indexed_at FROM repositories WHERE full_name = %s", (full_name,))
    assert cur.fetchone()[0] is not None
    cur.close()
    conn.close()


def test_evaluation_run_round_trips(monkeypatch):
    report = {"fixture_count": 2, "before_validation": {}, "after_validation": {}}
    run_id = evaluation_store.record_evaluation_run(report)
    try:
        row = queries.get_evaluation_run(run_id)
        assert row["report"]["fixture_count"] == 2
    finally:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM evaluation_runs WHERE id = %s", (run_id,))
        conn.commit()
        cur.close()
        conn.close()
