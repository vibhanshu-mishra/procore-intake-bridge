import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from app.config import Settings, get_settings
from app.security.admin_access import (
    ADMIN_SECURITY_HEADERS,
    AdminAuthDisabledError,
    AdminAuthInvalidError,
    AdminAuthMisconfiguredError,
    AdminAuthRequiredError,
    get_admin_auth_config_summary,
    require_admin_access,
)
from app.security.secrets import EnvSecretProvider, TestSecretProvider
from app.services.deployment_readiness import build_deployment_readiness_report
from app.services.secret_inventory import collect_admin_secret_refs

PRIMARY_REF = "PROCORE_INTAKE_SECRET_ADMIN_PRIMARY_TEST"
ROTATION_REF = "PROCORE_INTAKE_SECRET_ADMIN_ROTATION_TEST"


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def request(token: str | None = None, header: str = "X-Procore-Intake-Admin-Token"):
    headers = {header: token} if token is not None else {}
    return SimpleNamespace(headers=headers)


def test_local_optional_local_allows_no_token():
    result = require_admin_access(
        request(), settings(), EnvSecretProvider(settings())
    )
    assert result.authenticated is True
    assert result.token_used is False


def test_token_required_rejects_missing_and_invalid_without_echoing():
    configured = settings(
        admin_auth_mode="token_required",
        admin_token_secret_ref=PRIMARY_REF,
    )
    provider = TestSecretProvider(
        {PRIMARY_REF: "fake-valid-admin-token"}, configured
    )
    with pytest.raises(AdminAuthRequiredError):
        require_admin_access(request(), configured, provider)
    submitted = "fake-invalid-submitted-token"
    with pytest.raises(AdminAuthInvalidError) as error:
        require_admin_access(request(submitted), configured, provider)
    assert submitted not in str(error.value)


def test_primary_and_rotation_tokens_are_both_accepted():
    configured = settings(
        admin_auth_mode="token_required",
        admin_token_secret_ref=PRIMARY_REF,
        admin_token_rotation_secret_ref=ROTATION_REF,
    )
    provider = TestSecretProvider(
        {
            PRIMARY_REF: "fake-primary-token",
            ROTATION_REF: "fake-rotation-token",
        },
        configured,
    )
    for candidate in ("fake-primary-token", "fake-rotation-token"):
        result = require_admin_access(request(candidate), configured, provider)
        assert result.authenticated is True
        assert result.token_used is True


def test_disabled_unknown_and_missing_provider_fail_closed():
    with pytest.raises(AdminAuthDisabledError):
        require_admin_access(
            request(),
            settings(admin_auth_mode="disabled"),
            EnvSecretProvider(settings()),
        )
    unknown = Settings.model_construct(admin_auth_mode="unknown")
    with pytest.raises(AdminAuthMisconfiguredError):
        require_admin_access(request(), unknown, EnvSecretProvider(settings()))
    no_ref = settings(admin_auth_mode="token_required")
    with pytest.raises(AdminAuthMisconfiguredError):
        require_admin_access(
            request("fake-candidate"), no_ref, EnvSecretProvider(no_ref)
        )
    missing = settings(
        admin_auth_mode="token_required",
        admin_token_secret_ref=PRIMARY_REF,
    )
    with pytest.raises(AdminAuthMisconfiguredError):
        require_admin_access(
            request("fake-candidate"), missing, EnvSecretProvider(missing)
        )


def test_config_summary_is_sanitized(monkeypatch):
    token = "fake-never-print-admin-token"
    monkeypatch.setenv(PRIMARY_REF, token)
    summary = get_admin_auth_config_summary(
        settings(
            admin_auth_mode="token_required",
            admin_token_secret_ref=PRIMARY_REF,
        )
    )
    serialized = summary.model_dump_json()
    assert token not in serialized
    assert PRIMARY_REF not in serialized
    assert summary.primary_token_ref_configured is True
    assert summary.provider_health_status == "healthy"


def _configure_token_auth(monkeypatch):
    token = "fake-route-admin-token"
    monkeypatch.setenv("PROCORE_INTAKE_ADMIN_AUTH_MODE", "token_required")
    monkeypatch.setenv("PROCORE_INTAKE_ADMIN_TOKEN_SECRET_REF", PRIMARY_REF)
    monkeypatch.setenv(PRIMARY_REF, token)
    get_settings.cache_clear()
    return token


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/connections",
        "/admin/api/overview",
        "/admin/api/connections",
        "/admin/api/safety",
    ],
)
def test_admin_html_and_json_routes_require_token(client, monkeypatch, path):
    token = _configure_token_auth(monkeypatch)
    rejected = client.get(path)
    assert rejected.status_code == 401
    assert token not in rejected.text
    for header, value in ADMIN_SECURITY_HEADERS.items():
        assert rejected.headers[header] == value
    accepted = client.get(path, headers={"X-Procore-Intake-Admin-Token": token})
    assert accepted.status_code == 200
    for header, value in ADMIN_SECURITY_HEADERS.items():
        assert accepted.headers[header] == value
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "path",
    [
        "/deployment/readiness",
        "/deployment/safety",
        "/deployment/config-summary",
        "/deployment/secrets",
        "/deployment/migrations",
        "/deployment/storage",
    ],
)
def test_deployment_routes_are_protected_but_health_ready_are_public(
    client, monkeypatch, path
):
    token = _configure_token_auth(monkeypatch)
    assert client.get(path).status_code == 401
    accepted = client.get(
        path, headers={"X-Procore-Intake-Admin-Token": token}
    )
    assert accepted.status_code == 200
    assert accepted.headers["Cache-Control"] == "no-store"
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    get_settings.cache_clear()


def test_admin_readiness_blocks_unsafe_nonlocal_modes():
    local_optional = build_deployment_readiness_report(
        settings(environment="production")
    )
    assert any(
        finding.severity == "blocking"
        and "local-optional" in finding.message.casefold()
        for finding in local_optional.findings
    )
    missing_ref = build_deployment_readiness_report(
        settings(environment="production", admin_auth_mode="token_required")
    )
    assert any(
        "primary secret reference" in finding.message
        for finding in missing_ref.findings
    )
    unprotected = build_deployment_readiness_report(
        settings(
            environment="production",
            admin_auth_mode="token_required",
            admin_token_secret_ref=PRIMARY_REF,
            admin_auth_protect_deployment_routes=False,
        )
    )
    assert any(
        "deployment routes" in finding.message
        for finding in unprotected.findings
    )


def test_secret_inventory_masks_primary_and_rotation_refs():
    configured = settings(
        admin_auth_mode="token_required",
        admin_token_secret_ref=PRIMARY_REF,
        admin_token_rotation_secret_ref=ROTATION_REF,
    )
    items = collect_admin_secret_refs(configured)
    assert {item.purpose for item in items} == {
        "admin_auth_primary_token",
        "admin_auth_rotation_token",
    }
    serialized = json.dumps([item.model_dump() for item in items])
    assert PRIMARY_REF not in serialized
    assert ROTATION_REF not in serialized


def test_admin_auth_cli_default_and_strict_production():
    normal = subprocess.run(
        [".venv/bin/python", "scripts/check_admin_auth.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert normal.returncode == 0
    environment = os.environ.copy()
    environment["PROCORE_INTAKE_ENVIRONMENT"] = "production"
    strict = subprocess.run(
        [".venv/bin/python", "scripts/check_admin_auth.py", "--strict"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert strict.returncode != 0
    assert "token" not in strict.stdout.casefold() or "token_required" in strict.stdout
