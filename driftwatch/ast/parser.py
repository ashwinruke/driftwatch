import re

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
DEF_NODE_TYPES = {"function_definition", "class_definition"}
IMPORT_NODE_TYPES = {"import_statement", "import_from_statement"}


def changed_line_ranges(patch: str):
    """Parse a unified diff hunk header, return (start, end) line ranges in the NEW file."""
    ranges = []
    for match in re.finditer(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch):
        start = int(match.group(1))
        length = int(match.group(2)) if match.group(2) else 1
        ranges.append((start, start + length - 1))
    return ranges


def find_enclosing_chunks(source_bytes: bytes, changed_ranges: list[tuple[int, int]]):
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(source_bytes)

    chunks = []
    seen_ranges = set()

    def walk(node):
        if node.type in DEF_NODE_TYPES:
            node_start = node.start_point[0] + 1  # tree-sitter rows are 0-indexed
            node_end = node.end_point[0] + 1
            overlaps = any(node_start <= ce and node_end >= cs for cs, ce in changed_ranges)
            key = (node_start, node_end)
            if overlaps and key not in seen_ranges:
                seen_ranges.add(key)
                name_node = node.child_by_field_name("name")
                name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8") if name_node else "<anonymous>"
                text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                chunks.append({
                    "name": name,
                    "type": node.type,
                    "start_line": node_start,
                    "end_line": node_end,
                    "text": text,
                })
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return chunks


def find_uncovered_ranges(changed_ranges: list[tuple[int, int]], chunks: list[dict]) -> list[tuple[int, int]]:
    """Return contiguous changed sub-ranges not covered by any chunk's line
    span (e.g. a module-level assignment like a hardcoded secret, which has
    no enclosing function/class for find_enclosing_chunks to pick up)."""
    changed_lines = set()
    for start, end in changed_ranges:
        changed_lines.update(range(start, end + 1))

    covered_lines = set()
    for chunk in chunks:
        covered_lines.update(range(chunk["start_line"], chunk["end_line"] + 1))

    uncovered_lines = sorted(changed_lines - covered_lines)
    if not uncovered_lines:
        return []

    ranges = []
    range_start = uncovered_lines[0]
    prev = uncovered_lines[0]
    for line in uncovered_lines[1:]:
        if line != prev + 1:
            ranges.append((range_start, prev))
            range_start = line
        prev = line
    ranges.append((range_start, prev))
    return ranges


def extract_module_level_chunks(source_bytes: bytes, uncovered_ranges: list[tuple[int, int]]) -> list[dict]:
    """Wrap each uncovered changed range as its own pseudo-chunk, so it can
    flow through the same pipeline as function/class chunks."""
    lines = source_bytes.decode("utf-8", errors="replace").splitlines()
    chunks = []
    for start, end in uncovered_ranges:
        snippet = "\n".join(lines[start - 1:end])
        chunks.append({
            "name": "<module level>",
            "type": "module_level",
            "start_line": start,
            "end_line": end,
            "text": snippet,
        })
    return chunks


def find_anchor_line(chunk_start: int, chunk_end: int, changed_ranges: list[tuple[int, int]]) -> int:
    """First line within [chunk_start, chunk_end] that's actually part of
    the diff. GitHub's review-comment API rejects a line that isn't part of
    the diff, and a chunk's start_line (e.g. a function's `def` line) often
    isn't itself a changed line -- the chunk just overlaps changed lines
    inside it."""
    for line in range(chunk_start, chunk_end + 1):
        if any(cs <= line <= ce for cs, ce in changed_ranges):
            return line
    return chunk_start  # shouldn't happen: chunks only exist when they overlap a changed range


def extract_imports(source_bytes: bytes) -> list[str]:
    """Top-level import statements only -- cheap extra context for the LLM,
    not a full dependency graph."""
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(source_bytes)
    imports = []
    for node in tree.root_node.children:
        if node.type in IMPORT_NODE_TYPES:
            imports.append(source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace"))
    return imports


def extract_surrounding_lines(source_bytes: bytes, start_line: int, end_line: int, context: int = 3) -> tuple[str, str]:
    """A few lines of file context immediately before/after a chunk."""
    lines = source_bytes.decode("utf-8", errors="replace").splitlines()
    before_start = max(0, start_line - 1 - context)
    before = "\n".join(lines[before_start:start_line - 1])
    after_end = min(len(lines), end_line + context)
    after = "\n".join(lines[end_line:after_end])
    return before, after
