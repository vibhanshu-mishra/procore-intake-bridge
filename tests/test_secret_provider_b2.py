import json
import os
import subprocess

import pytest

from app.config import Settings
from app.security.secret_provider_factory import (
    build_secret_provider,
    summarize_secret_provider_config,
)
from app.security.secret_refs import (
    SecretRefError,
    is_placeholder_secret_ref,
    mask_secret_ref,
    normalize_secret_ref,
    validate_secret_ref,
)
from app.security.secrets import (
    DisabledSecretProvider,
    EnvSecretProvider,
    ExternalPlaceholderSecretProvider,
    SecretNotFoundError,
    SecretProviderMisconfiguredError,
    SecretProviderUnavailableError,
    TestSecretProvider,
)


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_secret_refs_require_prefix_but_allow_explicit_placeholders():
    configured = settings()
    valid = "PROCORE_INTAKE_SECRET_DMSA_CLIENT_SECRET"
    assert validate_secret_ref(valid, configured).name == valid
    with pytest.raises(SecretRefError):
        validate_secret_ref("customer_runtime_credential", configured)
    assert is_placeholder_secret_ref("demo/client-secret-placeholder")
    assert normalize_secret_ref(
        "demo/client-secret-placeholder", configured
    ).name.startswith(configured.secret_ref_prefix)


def test_raw_looking_secret_ref_is_rejected_without_echoing_value():
    raw = "sk-live-fake-sensitive-material"
    with pytest.raises(SecretRefError) as error:
        validate_secret_ref(raw, settings())
    assert raw not in str(error.value)


def test_ref_mask_does_not_reveal_full_name():
    ref = "PROCORE_INTAKE_SECRET_DMSA_CLIENT_SECRET"
    masked = mask_secret_ref(ref, settings())
    assert masked != ref
    assert masked.startswith("PROCORE_INTAKE_SECRET_")
    assert masked.endswith("CRET")
    assert "DMSA_CLIENT" not in masked


def test_env_provider_health_reports_presence_without_value(monkeypatch):
    ref = "PROCORE_INTAKE_SECRET_HEALTH_TEST"
    value = "fake-provider-health-value"
    monkeypatch.setenv(ref, value)
    provider = EnvSecretProvider(settings())
    assert provider.get_secret(ref) == value
    health = provider.health_check([ref, "PROCORE_INTAKE_SECRET_MISSING_TEST"])
    serialized = json.dumps(health, default=lambda item: item.__dict__)
    assert health.present_refs_count == 1
    assert health.missing_refs_count == 1
    assert value not in serialized
    assert ref not in serialized


def test_missing_env_ref_error_is_safe(monkeypatch):
    ref = "PROCORE_INTAKE_SECRET_MISSING_TEST"
    monkeypatch.delenv(ref, raising=False)
    with pytest.raises(SecretNotFoundError) as error:
        EnvSecretProvider(settings()).get_secret(ref)
    assert ref not in str(error.value)


def test_disabled_and_external_placeholder_fail_closed_without_network():
    ref = "PROCORE_INTAKE_SECRET_FAKE_TEST"
    with pytest.raises(SecretProviderUnavailableError):
        DisabledSecretProvider(settings()).get_secret(ref)
    external = ExternalPlaceholderSecretProvider(
        settings(secret_provider="external_placeholder")
    )
    with pytest.raises(SecretProviderUnavailableError) as error:
        external.get_secret(ref)
    assert "not implemented" in str(error.value)
    assert external.health_check([ref]).status == "unavailable"


def test_test_provider_requires_local_injected_values():
    ref = "PROCORE_INTAKE_SECRET_FAKE_TEST"
    provider = build_secret_provider(
        settings(secret_provider="test"), test_secrets={ref: "fake-test-value"}
    )
    assert isinstance(provider, TestSecretProvider)
    assert provider.get_secret(ref) == "fake-test-value"
    with pytest.raises(SecretProviderMisconfiguredError):
        build_secret_provider(settings(secret_provider="test"))
    with pytest.raises(SecretProviderMisconfiguredError):
        build_secret_provider(
            settings(secret_provider="test", environment="staging"),
            test_secrets={ref: "fake-test-value"},
        )


def test_factory_rejects_unknown_provider():
    configured = Settings.model_construct(secret_provider="unknown")
    with pytest.raises(SecretProviderMisconfiguredError):
        build_secret_provider(configured)


def test_provider_config_summary_contains_no_external_values():
    secret_like = "fake-private-provider-project"
    summary = summarize_secret_provider_config(
        settings(external_secret_provider_project=secret_like)
    )
    assert secret_like not in json.dumps(summary)
    assert summary["external_project_configured"] is True


def test_deployment_secrets_route_is_masked(client, connection):
    response = client.get("/deployment/secrets")
    assert response.status_code == 200
    serialized = response.text
    assert connection.secret_name not in serialized
    assert "values_exposed" in serialized
    assert response.json()["values_exposed"] is False


def test_secret_provider_cli_is_safe_and_strict_can_fail():
    normal = subprocess.run(
        [".venv/bin/python", "scripts/check_secret_provider.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert normal.returncode == 0
    environment = os.environ.copy()
    environment.update(
        {
            "PROCORE_INTAKE_ADMIN_REQUIRE_TOKEN": "true",
            "PROCORE_INTAKE_ADMIN_TOKEN_SECRET_NAME": (
                "PROCORE_INTAKE_SECRET_MISSING_ADMIN_TEST"
            ),
        }
    )
    strict = subprocess.run(
        [".venv/bin/python", "scripts/check_secret_provider.py", "--strict"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert strict.returncode != 0
    assert "MISSING_ADMIN_TEST" not in strict.stdout
    assert "fake-private" not in strict.stdout
