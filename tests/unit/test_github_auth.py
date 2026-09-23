import pytest

from driftwatch.github.auth import load_private_key


def test_prefers_env_var_over_file(monkeypatch, tmp_path):
    key_file = tmp_path / "key.pem"
    key_file.write_text("FILE_KEY")

    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "ENV_KEY")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))

    assert load_private_key() == "ENV_KEY"


def test_falls_back_to_file_when_env_var_absent(monkeypatch, tmp_path):
    key_file = tmp_path / "key.pem"
    key_file.write_text("FILE_KEY")

    monkeypatch.delenv("GITHUB_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))

    assert load_private_key() == "FILE_KEY"


def test_env_var_newlines_are_unescaped(monkeypatch):
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "line1\\nline2")
    assert load_private_key() == "line1\nline2"


def test_key_material_in_path_var_fails_cleanly_without_leaking_it(monkeypatch):
    # Regression test: a misconfigured GITHUB_PRIVATE_KEY_PATH containing the
    # actual key (instead of GITHUB_PRIVATE_KEY being set) must not leak the
    # key into an exception message.
    monkeypatch.delenv("GITHUB_PRIVATE_KEY", raising=False)
    key_contents = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpQ...\n-----END RSA PRIVATE KEY-----"
    monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", key_contents)

    with pytest.raises(RuntimeError) as exc_info:
        load_private_key()

    assert "MIIEpQ" not in str(exc_info.value)
