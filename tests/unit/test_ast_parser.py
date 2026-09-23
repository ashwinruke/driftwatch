from driftwatch.ast.parser import changed_line_ranges, find_enclosing_chunks


def test_changed_line_ranges_single_hunk():
    patch = "@@ -10,5 +10,7 @@ def foo():\n some context\n+added line\n"
    assert changed_line_ranges(patch) == [(10, 16)]


def test_changed_line_ranges_no_length_defaults_to_one_line():
    patch = "@@ -1 +5 @@\n"
    assert changed_line_ranges(patch) == [(5, 5)]


def test_changed_line_ranges_multiple_hunks():
    patch = "@@ -1,3 +1,3 @@\n...\n@@ -20,2 +22,4 @@\n..."
    assert changed_line_ranges(patch) == [(1, 3), (22, 25)]


SOURCE = b"""def unchanged():
    return 1


def changed():
    return 2


class UnchangedClass:
    pass
"""


def test_find_enclosing_chunks_only_returns_overlapping_functions():
    # "def changed():" starts on line 5 of SOURCE.
    chunks = find_enclosing_chunks(SOURCE, [(5, 6)])
    assert len(chunks) == 1
    assert chunks[0]["name"] == "changed"
    assert chunks[0]["type"] == "function_definition"


def test_find_enclosing_chunks_dedupes_overlapping_ranges():
    # Two changed ranges that both fall inside the same function should
    # produce a single chunk, not two.
    chunks = find_enclosing_chunks(SOURCE, [(5, 5), (6, 6)])
    assert len(chunks) == 1


def test_find_enclosing_chunks_ignores_unrelated_definitions():
    chunks = find_enclosing_chunks(SOURCE, [(5, 6)])
    names = [c["name"] for c in chunks]
    assert "unchanged" not in names
    assert "UnchangedClass" not in names
