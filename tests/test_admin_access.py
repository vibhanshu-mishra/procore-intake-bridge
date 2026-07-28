from types import SimpleNamespace

import pytest

from app.config import Settings
from app.security.admin_access import (
    AdminAccessError,
    mask_identifier,
    redact_admin_value,
    require_admin_access,
)
from app.security.secret_provider import EnvSecretProvider


def _request(token: str | None = None):
    headers = {}
    if token is not None:
        headers["x-procore-intake-admin-token"] = token
    return SimpleNamespace(headers=headers)


def _settings(**values):
    return Settings(_env_file=None, **values)


def test_local_admin_access_is_allowed_without_token():
    require_admin_access(_request(), _settings(), EnvSecretProvider())


def test_disabled_admin_fails_as_not_found():
    with pytest.raises(AdminAccessError) as error:
        require_admin_access(
            _request(),
            _settings(admin_dashboard_enabled=False),
            EnvSecretProvider(),
        )
    assert error.value.status_code == 404


def test_token_guard_fails_closed_and_never_leaks_token(monkeypatch):
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_ADMIN_TEST", "correct-token")
    settings = _settings(
        admin_require_token=True,
        admin_token_secret_name="admin_test",
    )
    for supplied, status in ((None, 401), ("wrong-token", 403)):
        with pytest.raises(AdminAccessError) as error:
            require_admin_access(_request(supplied), settings, EnvSecretProvider())
        assert error.value.status_code == status
        assert "correct-token" not in str(error.value)
        assert "wrong-token" not in str(error.value)
    require_admin_access(_request("correct-token"), settings, EnvSecretProvider())


def test_token_guard_requires_a_resolvable_secret_reference(monkeypatch):
    with pytest.raises(AdminAccessError) as blank:
        require_admin_access(
            _request("anything"),
            _settings(admin_require_token=True),
            EnvSecretProvider(),
        )
    assert blank.value.status_code == 503

    monkeypatch.delenv("PROCORE_INTAKE_SECRET_MISSING_ADMIN", raising=False)
    with pytest.raises(AdminAccessError) as missing:
        require_admin_access(
            _request("anything"),
            _settings(
                admin_require_token=True,
                admin_token_secret_name="missing_admin",
            ),
            EnvSecretProvider(),
        )
    assert missing.value.status_code == 503


def test_admin_masking_and_recursive_redaction():
    assert mask_identifier("project-1001") == "pro***001"
    assert mask_identifier("abc") == "***"
    assert redact_admin_value(
        {
            "token": "never-show",
            "nested": {
                "source_url": "https://example.invalid/signed",
                "path": "/private/tmp/customer.txt",
            },
        }
    ) == {
        "token": "[REDACTED]",
        "nested": {
            "source_url": "[REDACTED]",
            "path": "[REDACTED_PATH]",
        },
    }
