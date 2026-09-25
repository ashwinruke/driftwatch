import driftwatch.observability.tracing as tracing


def test_disabled_by_default_in_test_env():
    # conftest.py forces LANGFUSE_PUBLIC_KEY off, so tracing must be off
    # regardless of what the developer's local .env has configured.
    assert tracing.ENABLED is False


def test_traced_generation_is_identity_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "ENABLED", False)

    def original(x):
        return x + 1

    wrapped = tracing.traced_generation("some-generation")(original)

    assert wrapped is original
    assert wrapped(1) == 2


def test_traced_span_is_identity_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "ENABLED", False)

    def original(x):
        return x * 2

    wrapped = tracing.traced_span("some-span")(original)

    assert wrapped is original
    assert wrapped(3) == 6


def test_tag_current_run_is_noop_when_disabled(monkeypatch):
    # Must not raise even with ENABLED forced off (get_client would be None
    # in that state if the module had been imported that way).
    monkeypatch.setattr(tracing, "ENABLED", False)
    tracing.tag_current_run(repository="owner/repo", pull_request=1)


def test_traced_generation_wraps_when_enabled(monkeypatch):
    calls = {}

    def fake_observe(as_type=None, name=None):
        calls["as_type"] = as_type
        calls["name"] = name

        def decorator(func):
            def inner(*args, **kwargs):
                calls["called"] = True
                return func(*args, **kwargs)

            return inner

        return decorator

    monkeypatch.setattr(tracing, "ENABLED", True)
    monkeypatch.setattr(tracing, "observe", fake_observe)

    def original(x):
        return x + 1

    wrapped = tracing.traced_generation("some-generation")(original)

    assert wrapped is not original
    assert wrapped(1) == 2
    assert calls == {"as_type": "generation", "name": "some-generation", "called": True}


def test_tag_current_run_updates_current_span_when_enabled(monkeypatch):
    captured = {}

    class FakeClient:
        def update_current_span(self, metadata=None):
            captured["metadata"] = metadata

    monkeypatch.setattr(tracing, "ENABLED", True)
    monkeypatch.setattr(tracing, "get_client", lambda: FakeClient())

    tracing.tag_current_run(repository="owner/repo", pull_request=7)

    assert captured["metadata"] == {"repository": "owner/repo", "pull_request": 7}
