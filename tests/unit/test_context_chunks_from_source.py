from driftwatch.review.context import extract_chunks_from_source

SOURCE = b"""import os

API_KEY = "sk-hardcoded-secret"


def changed():
    return 2
"""


def test_produces_function_and_module_level_chunks_for_whole_file():
    num_lines = len(SOURCE.decode().splitlines())
    chunks = extract_chunks_from_source(SOURCE, "app.py", [(1, num_lines)], include_module_level=True)

    types = {c["type"] for c in chunks}
    assert "function_definition" in types
    assert "module_level" in types
    assert all(c["file"] == "app.py" for c in chunks)


def test_include_module_level_false_matches_old_extract_changed_chunks_default():
    num_lines = len(SOURCE.decode().splitlines())
    chunks = extract_chunks_from_source(SOURCE, "app.py", [(1, num_lines)], include_module_level=False)

    # Only the function chunk, no module-level fallback, no anchor_line/diff_ranges attached
    assert len(chunks) == 1
    assert chunks[0]["type"] == "function_definition"
    assert "anchor_line" not in chunks[0]
    assert "diff_ranges" not in chunks[0]


def test_attaches_anchor_line_and_diff_ranges_when_module_level_enabled():
    num_lines = len(SOURCE.decode().splitlines())
    changed_ranges = [(1, num_lines)]
    chunks = extract_chunks_from_source(SOURCE, "app.py", changed_ranges, include_module_level=True)

    for chunk in chunks:
        assert "anchor_line" in chunk
        assert chunk["diff_ranges"] == changed_ranges
        assert "imports" in chunk
