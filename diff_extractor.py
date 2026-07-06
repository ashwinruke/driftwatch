import httpx
import base64
import re
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import logging
logger = logging.getLogger("driftwatch")

PY_LANGUAGE = Language(tspython.language())
DEF_NODE_TYPES = {"function_definition", "class_definition"}


def get_pr_files(owner: str, repo: str, pr_number: int, token: str):
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()
    return resp.json()

def get_blob_content(owner: str, repo: str, blob_sha: str, token: str) -> bytes:
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{blob_sha}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()
    return base64.b64decode(resp.json()["content"])

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

def extract_changed_chunks(owner: str, repo: str, pr_number: int, token: str):
    files = get_pr_files(owner, repo, pr_number, token)
    results = []

    for f in files:
        path = f["filename"]
        if not path.endswith(".py") or f["status"] == "removed":
            continue

        patch = f.get("patch")
        if not patch:
            logger.info(f"Skipping {path}: no patch available (binary file or diff too large for GitHub to include)")
            continue

        ranges = changed_line_ranges(patch)
        if not ranges:
            continue

        source_bytes = get_blob_content(owner, repo, f["sha"], token)
        for chunk in find_enclosing_chunks(source_bytes, ranges):
            chunk["file"] = path
            results.append(chunk)

    return results