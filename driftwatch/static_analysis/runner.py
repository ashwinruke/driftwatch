import tempfile
from pathlib import Path

from driftwatch.static_analysis import bandit, semgrep


def run_static_analysis(chunks: list[dict]) -> None:
    """Writes every chunk's text to its own file in one temp directory,
    runs Semgrep and Bandit once each against that directory (not once per
    chunk -- each tool's CLI startup alone is ~1-3s), then attaches
    chunk["static_matches"] to each chunk in place, with line numbers
    remapped from chunk-relative to the real file's line numbers using
    each chunk's start_line offset. Mutates chunks."""
    if not chunks:
        return

    with tempfile.TemporaryDirectory(prefix="driftwatch_static_") as tmpdir:
        filename_to_chunk = {}
        for i, chunk in enumerate(chunks):
            filename = f"chunk_{i}.py"
            filename_to_chunk[filename] = chunk
            (Path(tmpdir) / filename).write_text(chunk["text"], encoding="utf-8")

        semgrep_matches = semgrep.run(tmpdir)
        bandit_matches = bandit.run(tmpdir)

    for filename, chunk in filename_to_chunk.items():
        offset = chunk["start_line"] - 1
        matches = semgrep_matches.get(filename, []) + bandit_matches.get(filename, [])
        for match in matches:
            match.line = (match.line or 0) + offset
            match.file_path = chunk["file"]
        chunk["static_matches"] = matches
