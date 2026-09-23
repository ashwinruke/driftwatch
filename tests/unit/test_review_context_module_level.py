from driftwatch.ast.parser import (
    extract_imports,
    extract_module_level_chunks,
    find_anchor_line,
    find_enclosing_chunks,
    find_uncovered_ranges,
)

SOURCE = b"""import os
import sys

API_KEY = "sk-hardcoded-secret"


def changed():
    return 2
"""


def test_find_uncovered_ranges_detects_module_level_change():
    # line 4 (API_KEY = ...) is changed, but not inside any function/class
    changed_ranges = [(4, 4)]
    chunks = find_enclosing_chunks(SOURCE, changed_ranges)
    assert chunks == []
    assert find_uncovered_ranges(changed_ranges, chunks) == [(4, 4)]


def test_find_uncovered_ranges_excludes_covered_lines():
    changed_ranges = [(7, 8)]  # inside `changed()`
    chunks = find_enclosing_chunks(SOURCE, changed_ranges)
    assert len(chunks) == 1
    assert find_uncovered_ranges(changed_ranges, chunks) == []


def test_extract_module_level_chunks_produces_pseudo_chunk():
    chunks = extract_module_level_chunks(SOURCE, [(4, 4)])
    assert len(chunks) == 1
    assert chunks[0]["type"] == "module_level"
    assert "API_KEY" in chunks[0]["text"]


def test_find_anchor_line_picks_first_changed_line_in_range():
    # chunk spans lines 7-8, but only line 8 is actually changed
    assert find_anchor_line(7, 8, [(8, 8)]) == 8


def test_extract_imports_returns_top_level_imports():
    imports = extract_imports(SOURCE)
    assert "import os" in imports
    assert "import sys" in imports
