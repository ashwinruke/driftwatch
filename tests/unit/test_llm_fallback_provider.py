import json

from driftwatch.llm.provider import FallbackProvider, GroqProvider
from driftwatch.review.models import CandidateFinding


def _finding() -> CandidateFinding:
    return CandidateFinding(
        category="security", severity="high", file_path="app.py",
        start_line=1, end_line=2, title="t", description="d",
        reasoning_summary="r", confidence=0.8,
    )


class _StubProvider:
    def __init__(self, result=None, exc=None):
        self._result = result if result is not None else []
        self._exc = exc
        self.calls = 0

    def generate_findings(self, prompt):
        self.calls += 1
        if self._exc:
            raise self._exc
        return self._result


def test_fallback_not_used_when_primary_succeeds():
    primary = _StubProvider(result=[_finding()])
    fallback = _StubProvider(result=[])
    provider = FallbackProvider(primary, fallback)

    result = provider.generate_findings("prompt")

    assert len(result) == 1
    assert fallback.calls == 0


def test_fallback_used_when_primary_raises():
    primary = _StubProvider(exc=RuntimeError("503 unavailable"))
    fallback = _StubProvider(result=[_finding()])
    provider = FallbackProvider(primary, fallback)

    result = provider.generate_findings("prompt")

    assert len(result) == 1
    assert primary.calls == 1
    assert fallback.calls == 1


def test_fallback_exception_propagates_if_both_fail():
    primary = _StubProvider(exc=RuntimeError("primary down"))
    fallback = _StubProvider(exc=RuntimeError("fallback down"))
    provider = FallbackProvider(primary, fallback)

    try:
        provider.generate_findings("prompt")
        assert False, "expected an exception"
    except RuntimeError as e:
        assert "fallback down" in str(e)


def test_groq_provider_sends_expected_request(monkeypatch):
    import driftwatch.llm.provider as provider_module

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"findings": []})}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(provider_module.httpx, "post", fake_post)
    monkeypatch.setattr(provider_module.config, "GROQ_API_KEY", "fake-key")

    provider = GroqProvider(model="openai/gpt-oss-120b")
    result = provider.generate_findings("analyze this code")

    assert result == []
    assert captured["url"] == GroqProvider.API_URL
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
    assert captured["json"]["model"] == "openai/gpt-oss-120b"
    assert "analyze this code" in captured["json"]["messages"][0]["content"]
    assert captured["json"]["response_format"] == {"type": "json_object"}
