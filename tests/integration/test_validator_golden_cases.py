"""Spec §35's golden evaluation cases, run through the real validate()
pipeline (including real, offline Semgrep/Bandit corroboration). This is
Phase 2's concrete demonstration of the validation layer actually working,
ahead of Phase 3's formal evaluation harness."""

from driftwatch.review.models import CandidateFinding
from driftwatch.static_analysis.runner import run_static_analysis
from driftwatch.validation.validator import validate


def _chunk(text: str, start_line: int = 1, end_line: int | None = None) -> dict:
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    chunk = {
        "file": "app.py",
        "start_line": start_line,
        "end_line": end_line or (start_line + lines - 1),
        "type": "function_definition",
        "diff_ranges": [(start_line, end_line or (start_line + lines - 1))],
        "text": text,
    }
    run_static_analysis([chunk])
    return chunk


def test_case_a_sql_injection_is_accepted():
    code = (
        "def run_query(cursor, user_id):\n"
        '    query = f"SELECT * FROM users WHERE id = {user_id}"\n'
        "    cursor.execute(query)\n"
    )
    chunk = _chunk(code)
    candidate = CandidateFinding(
        category="security", severity="high", file_path="app.py",
        start_line=chunk["start_line"] + 1, end_line=chunk["start_line"] + 2,
        title="SQL injection", description="user_id is interpolated directly into the query string.",
        reasoning_summary="f-string builds SQL with unsanitized input, matches Semgrep's sql-injection-string-building rule.",
        confidence=0.9,
    )
    result = validate(candidate, chunk)
    assert result.status == "accepted"


def test_case_b_safe_parameterized_sql_has_no_static_corroboration():
    code = (
        "def run_query(cursor, user_id):\n"
        '    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n'
    )
    chunk = _chunk(code)
    assert chunk["static_matches"] == []  # nothing for a validator to (mis)corroborate


def test_case_c_unsafe_shell_exec_is_accepted():
    code = (
        "def run(user_input):\n"
        "    subprocess.run(user_input, shell=True)\n"
    )
    chunk = _chunk(code)
    candidate = CandidateFinding(
        category="security", severity="high", file_path="app.py",
        start_line=chunk["start_line"] + 1, end_line=chunk["start_line"] + 1,
        title="Unsafe shell execution", description="User-controlled input reaches subprocess.run with shell=True.",
        reasoning_summary="shell=True with unsanitized input allows command injection.",
        confidence=0.85,
    )
    result = validate(candidate, chunk)
    assert result.status == "accepted"


def test_case_c_safe_subprocess_has_no_shell_injection_corroboration():
    # Bandit generically flags any subprocess call at low severity
    # (B603/B607, "review this") regardless of shell=True -- that's
    # expected noise, not a vulnerability signal. What must NOT appear is
    # a shell-injection-specific match, which is what the rest of the
    # pipeline actually cares about.
    code = (
        "def run(tool_name, user_input):\n"
        '    subprocess.run(["tool", "--name", user_input], check=True)\n'
    )
    chunk = _chunk(code)
    assert not any("shell" in m.message.lower() for m in chunk["static_matches"])


def test_case_d_harmless_refactor_has_no_static_corroboration():
    code = (
        "def add(a, b):\n"
        "    total = a + b\n"
        "    return total\n"
    )
    chunk = _chunk(code)
    assert chunk["static_matches"] == []


def test_overstated_wording_downgrades_an_otherwise_acceptable_finding():
    code = (
        "def run(user_input):\n"
        "    subprocess.run(user_input, shell=True)\n"
    )
    chunk = _chunk(code)
    candidate = CandidateFinding(
        category="security", severity="high", file_path="app.py",
        start_line=chunk["start_line"] + 1, end_line=chunk["start_line"] + 1,
        title="Unsafe shell execution",
        description="This will always cause a remote code execution vulnerability, guaranteed.",
        reasoning_summary="shell=True with unsanitized input.",
        confidence=0.85,
    )
    result = validate(candidate, chunk)
    # Same evidence as test_case_c above, but overstated wording should
    # pull the score down relative to the grounded version.
    grounded_result = validate(
        CandidateFinding(**{**candidate.model_dump(), "description": "User-controlled input reaches subprocess.run with shell=True."}),
        chunk,
    )
    assert result.score < grounded_result.score
