import hashlib
import hmac

import pytest

from app.config import Settings
from app.security.secret_provider import EnvSecretProvider
from app.security.webhook_signature import (
    WebhookSignatureError,
    verify_webhook_signature,
)


def test_signature_skipped_when_not_required():
    result = verify_webhook_signature(
        b"{}",
        {},
        EnvSecretProvider(),
        Settings(_env_file=None, require_webhook_signature=False),
    )
    assert result.status == "not_configured"
    assert result.verified is False


def test_required_signature_without_secret_fails_closed():
    with pytest.raises(WebhookSignatureError) as error:
        verify_webhook_signature(
            b"{}",
            {},
            EnvSecretProvider(),
            Settings(
                _env_file=None,
                require_webhook_signature=True,
                webhook_secret_name="",
            ),
        )
    assert "secret reference" in str(error.value)


def test_valid_fake_hmac_signature(monkeypatch):
    body = b'{"event_id":"synthetic"}'
    secret = "fake-webhook-secret"
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_WEBHOOK_TEST", secret)
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    result = verify_webhook_signature(
        body,
        {"X-Configured-Signature": f"sha256={signature}"},
        EnvSecretProvider(),
        Settings(
            _env_file=None,
            require_webhook_signature=True,
            webhook_secret_name="webhook_test",
            webhook_signature_header="x-configured-signature",
        ),
    )
    assert result.status == "valid"
    assert result.verified is True
    assert secret not in result.message


def test_invalid_signature_does_not_echo_values(monkeypatch):
    secret = "never-echo-this-secret"
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_WEBHOOK_TEST", secret)
    with pytest.raises(WebhookSignatureError) as error:
        verify_webhook_signature(
            b"{}",
            {"x-procore-signature": "invalid-signature-value"},
            EnvSecretProvider(),
            Settings(
                _env_file=None,
                require_webhook_signature=True,
                webhook_secret_name="webhook_test",
            ),
        )
    assert secret not in str(error.value)
    assert "invalid-signature-value" not in str(error.value)
