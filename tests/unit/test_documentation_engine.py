from driftwatch.analyzers.documentation import engine


def _chunk(**overrides):
    chunk = {
        "name": "run_query",
        "type": "function_definition",
        "start_line": 10,
        "end_line": 12,
        "text": "def run_query(): ...",
        "file": "app.py",
    }
    chunk.update(overrides)
    return chunk


def _section(**overrides):
    section = {
        "file_path": "README.md",
        "heading": "Usage",
        "content": "Call run_query() with no arguments.",
        "similarity": 0.83,
    }
    section.update(overrides)
    return section


def test_outdated_verdict_produces_a_documentation_candidate(monkeypatch):
    monkeypatch.setattr(engine, "find_stale_sections", lambda repo, chunk: [_section()])
    monkeypatch.setattr(engine, "draft_update", lambda chunk, section: {
        "verdict": "OUTDATED", "draft": "Call run_query(user_id) with a user_id argument.",
        "reason": "run_query now requires a user_id parameter.", "raw": "...",
    })

    chunk = _chunk()
    results = engine.analyze_chunk(chunk, "owner/repo")

    assert len(results) == 1
    candidate, returned_chunk = results[0]
    assert candidate.category == "documentation"
    assert candidate.file_path == "README.md"
    assert candidate.start_line == 1 and candidate.end_line == 1
    assert candidate.title == "Usage"
    assert candidate.confidence == 0.83
    assert candidate.suggested_fix == "Call run_query(user_id) with a user_id argument."
    assert returned_chunk is chunk


def test_not_outdated_verdict_produces_no_candidate(monkeypatch):
    monkeypatch.setattr(engine, "find_stale_sections", lambda repo, chunk: [_section()])
    monkeypatch.setattr(engine, "draft_update", lambda chunk, section: {
        "verdict": "NOT_OUTDATED", "draft": "N/A", "reason": "Unrelated to this section.", "raw": "...",
    })

    results = engine.analyze_chunk(_chunk(), "owner/repo")
    assert results == []


def test_no_stale_sections_produces_no_candidates(monkeypatch):
    monkeypatch.setattr(engine, "find_stale_sections", lambda repo, chunk: [])
    results = engine.analyze_chunk(_chunk(), "owner/repo")
    assert results == []


def test_missing_heading_falls_back_to_file_path_as_title(monkeypatch):
    monkeypatch.setattr(engine, "find_stale_sections", lambda repo, chunk: [_section(heading=None)])
    monkeypatch.setattr(engine, "draft_update", lambda chunk, section: {
        "verdict": "OUTDATED", "draft": "fix", "reason": "reason", "raw": "...",
    })

    candidate, _ = engine.analyze_chunk(_chunk(), "owner/repo")[0]
    assert candidate.title == "README.md"
