import hashlib
import hmac

from driftwatch.github.webhooks import verify_signature


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    body = b'{"key": "value"}'
    secret = "my-secret"
    assert verify_signature(body, _sign(body, secret), secret) is True


def test_invalid_signature_rejected():
    body = b'{"key": "value"}'
    assert verify_signature(body, "sha256=deadbeef", "my-secret") is False


def test_missing_signature_rejected():
    body = b'{"key": "value"}'
    assert verify_signature(body, "", "my-secret") is False


def test_signature_for_tampered_body_rejected():
    secret = "my-secret"
    signature = _sign(b'{"key": "value"}', secret)
    assert verify_signature(b'{"key": "tampered"}', signature, secret) is False
