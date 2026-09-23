import json

from driftwatch.llm.provider import parse_findings_response


def test_parses_valid_findings():
    raw = json.dumps([
        {
            "category": "security",
            "severity": "high",
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 2,
            "title": "Hardcoded secret",
            "description": "desc",
            "reasoning_summary": "reason",
            "confidence": 0.9,
        }
    ])
    findings = parse_findings_response(raw)
    assert len(findings) == 1
    assert findings[0].title == "Hardcoded secret"


def test_empty_array_returns_no_findings():
    assert parse_findings_response("[]") == []


def test_malformed_json_returns_no_findings():
    assert parse_findings_response("not json") == []


def test_skips_malformed_individual_findings():
    raw = json.dumps([{"category": "security"}])  # missing required fields
    assert parse_findings_response(raw) == []


def test_parses_findings_wrapped_in_object():
    # Groq/OpenAI-compatible json_object mode returns {"findings": [...]},
    # not a bare array like Gemini's response_schema enforces.
    raw = json.dumps({"findings": [
        {
            "category": "security",
            "severity": "high",
            "file_path": "app.py",
            "start_line": 1,
            "end_line": 2,
            "title": "Hardcoded secret",
            "description": "desc",
            "reasoning_summary": "reason",
            "confidence": 0.9,
        }
    ]})
    findings = parse_findings_response(raw)
    assert len(findings) == 1
    assert findings[0].title == "Hardcoded secret"


def test_empty_findings_object_returns_no_findings():
    assert parse_findings_response('{"findings": []}') == []


def test_object_without_findings_key_returns_no_findings():
    assert parse_findings_response('{"unexpected": "shape"}') == []
