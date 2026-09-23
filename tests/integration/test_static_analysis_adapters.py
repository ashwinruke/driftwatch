"""Real, offline subprocess runs of Semgrep and Bandit against known
vulnerable/safe snippets. No network or GitHub/Gemini access needed --
Semgrep uses the bundled local ruleset (driftwatch/static_analysis/rules),
not the registry."""

from driftwatch.static_analysis.runner import run_static_analysis

VULNERABLE_CHUNK = {
    "file": "app.py",
    "start_line": 5,
    "end_line": 7,
    "text": (
        "def run(user_input):\n"
        "    import subprocess\n"
        "    subprocess.run(user_input, shell=True)\n"
    ),
}

SAFE_CHUNK = {
    "file": "app.py",
    "start_line": 5,
    "end_line": 7,
    "text": (
        "def run(args):\n"
        "    import subprocess\n"
        "    subprocess.run(args, check=True)\n"
    ),
}


def test_semgrep_and_bandit_flag_shell_true():
    chunks = [dict(VULNERABLE_CHUNK)]
    run_static_analysis(chunks)
    matches = chunks[0]["static_matches"]
    assert len(matches) > 0
    tools = {m.tool for m in matches}
    assert "semgrep" in tools or "bandit" in tools


def test_matches_are_remapped_to_real_file_line_numbers():
    chunks = [dict(VULNERABLE_CHUNK)]
    run_static_analysis(chunks)
    matches = chunks[0]["static_matches"]
    # The shell=True call is on chunk-relative line 3 (start_line=5 -> offset 4),
    # so the remapped line should be >= start_line, not a raw 1-based chunk line.
    assert all(m.line >= VULNERABLE_CHUNK["start_line"] for m in matches)


def test_safe_subprocess_call_produces_no_shell_true_match():
    chunks = [dict(SAFE_CHUNK)]
    run_static_analysis(chunks)
    matches = chunks[0]["static_matches"]
    assert not any("shell" in m.message.lower() for m in matches)


def test_no_chunks_is_a_noop():
    run_static_analysis([])  # must not raise
