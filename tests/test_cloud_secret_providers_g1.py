import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas.secrets import CloudSecretProviderKind, CloudSecretProviderStatus
from app.security.secret_refs import SecretRefError, validate_cloud_secret_ref
from app.security.secrets import (
    CLOUD_CONFIRMATION_PHRASE,
    AwsSecretsManagerProvider,
    AzureKeyVaultSecretProvider,
    GcpSecretManagerProvider,
    SecretProviderBlockedError,
    SecretProviderResolutionError,
)
from app.services.secrets import build_cloud_secret_provider_health

ROOT = Path(__file__).resolve().parents[1]


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("kind", "enabled_field"),
    [
        (CloudSecretProviderKind.AWS_SECRETS_MANAGER, "aws_secrets_enabled"),
        (CloudSecretProviderKind.AZURE_KEY_VAULT, "azure_key_vault_enabled"),
        (CloudSecretProviderKind.GCP_SECRET_MANAGER, "gcp_secret_manager_enabled"),
    ],
)
def test_cloud_providers_are_disabled_by_default(kind, enabled_field):
    settings = configured()
    assert getattr(settings, enabled_field) is False
    health = build_cloud_secret_provider_health(kind, settings)
    assert health.status is CloudSecretProviderStatus.DISABLED
    assert health.resolution_allowed is False
    assert health.external_calls is False
    assert health.health_network_check_attempted is False


def test_cloud_network_and_confirmation_are_disabled_by_default():
    settings = configured()
    assert settings.secret_provider_cloud_network_enabled is False
    assert settings.secret_provider_cloud_confirmation == ""


def test_missing_confirmation_blocks_resolution(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    provider = AwsSecretsManagerProvider(
        configured(
            secret_provider="aws_secrets_manager",
            secret_provider_allow_cloud=True,
            secret_provider_cloud_network_enabled=True,
            aws_secrets_enabled=True,
        ),
        client=SimpleNamespace(get_secret_value=lambda **_: {"SecretString": "never"}),
    )
    with pytest.raises(SecretProviderBlockedError):
        provider.get_secret("AWS_SECRET_REF_PLACEHOLDER_NAME")


def test_missing_dependency_is_reported_without_traceback(monkeypatch):
    monkeypatch.setattr(AwsSecretsManagerProvider, "_dependency_present", lambda self: False)
    health = build_cloud_secret_provider_health(
        CloudSecretProviderKind.AWS_SECRETS_MANAGER,
        configured(
            secret_provider="aws_secrets_manager",
            secret_provider_allow_cloud=True,
            aws_secrets_enabled=True,
        ),
    )
    assert health.status is CloudSecretProviderStatus.DEPENDENCY_MISSING
    assert health.dependency_missing is True
    assert "traceback" not in health.model_dump_json().casefold()


def test_missing_config_reports_needs_configuration(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setattr(AwsSecretsManagerProvider, "_dependency_present", lambda self: True)
    health = build_cloud_secret_provider_health(
        CloudSecretProviderKind.AWS_SECRETS_MANAGER,
        configured(
            secret_provider="aws_secrets_manager",
            secret_provider_allow_cloud=True,
            aws_secrets_enabled=True,
        ),
    )
    assert health.status is CloudSecretProviderStatus.NEEDS_CONFIGURATION


def test_unselected_cloud_provider_cannot_resolve(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    client = AwsClient({"SecretString": "must-not-appear-unselected-value"})
    provider = AwsSecretsManagerProvider(
        configured(
            secret_provider="env",
            secret_provider_allow_cloud=True,
            secret_provider_cloud_network_enabled=True,
            secret_provider_cloud_confirmation=CLOUD_CONFIRMATION_PHRASE,
            aws_secrets_enabled=True,
        ),
        client=client,
    )
    with pytest.raises(SecretProviderBlockedError):
        provider.get_secret("AWS_SECRET_REF_PLACEHOLDER_NAME")
    assert client.calls == 0


class AwsClient:
    def __init__(self, response=None, error=None):
        self.response = response or {}
        self.error = error
        self.calls = 0

    def get_secret_value(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


def aws_provider(monkeypatch, client):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    return AwsSecretsManagerProvider(
        configured(
            secret_provider="aws_secrets_manager",
            secret_provider_allow_cloud=True,
            secret_provider_cloud_network_enabled=True,
            secret_provider_cloud_confirmation=CLOUD_CONFIRMATION_PHRASE,
            aws_secrets_enabled=True,
        ),
        client=client,
    )


def test_aws_simple_name_resolves_internal_value_without_reporting(monkeypatch):
    value = "must-not-appear-aws-secret-value"
    client = AwsClient({"SecretString": value})
    provider = aws_provider(monkeypatch, client)
    assert provider.get_secret("AWS_SECRET_REF_PLACEHOLDER_NAME") == value
    report = provider.health_check(["AWS_SECRET_REF_PLACEHOLDER_NAME"])
    assert value not in json.dumps(report, default=lambda item: item.__dict__)
    assert client.calls == 1


def test_aws_default_health_does_not_contact_client(monkeypatch):
    client = AwsClient({"SecretString": "must-not-appear-health-value"})
    provider = aws_provider(monkeypatch, client)
    provider.health_check(["AWS_SECRET_REF_PLACEHOLDER_NAME"])
    assert client.calls == 0


def test_aws_binary_secret_is_blocked(monkeypatch):
    provider = aws_provider(monkeypatch, AwsClient({"SecretBinary": b"fake-binary"}))
    with pytest.raises(SecretProviderBlockedError):
        provider.get_secret("AWS_SECRET_REF_PLACEHOLDER_NAME")


def test_aws_sdk_error_is_sanitized(monkeypatch):
    marker = "must-not-appear-aws-resource-or-error"
    provider = aws_provider(monkeypatch, AwsClient(error=RuntimeError(marker)))
    with pytest.raises(SecretProviderResolutionError) as error:
        provider.get_secret("AWS_SECRET_REF_PLACEHOLDER_NAME")
    assert marker not in str(error.value)


def test_aws_resource_identifier_blocked_by_default():
    with pytest.raises(SecretRefError):
        validate_cloud_secret_ref(
            "arn:aws:secretsmanager:example-region-placeholder:"
            "123456789012:secret:fake-placeholder",
            "aws_secrets_manager",
        )


class AzureClient:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.calls = 0

    def get_secret(self, name):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(value=self.value)


def azure_provider(monkeypatch, client):
    monkeypatch.setenv("AZURE_KEY_VAULT_NAME", "example-vault-placeholder")
    return AzureKeyVaultSecretProvider(
        configured(
            secret_provider="azure_key_vault",
            secret_provider_allow_cloud=True,
            secret_provider_cloud_network_enabled=True,
            secret_provider_cloud_confirmation=CLOUD_CONFIRMATION_PHRASE,
            azure_key_vault_enabled=True,
        ),
        client=client,
    )


def test_azure_mocked_resolution_is_internal_and_health_offline(monkeypatch):
    value = "must-not-appear-azure-secret-value"
    client = AzureClient(value=value)
    provider = azure_provider(monkeypatch, client)
    provider.health_check(["AZURE_SECRET_REF_PLACEHOLDER_NAME"])
    assert client.calls == 0
    assert provider.get_secret("AZURE_SECRET_REF_PLACEHOLDER_NAME") == value
    assert value not in json.dumps(provider.describe_ref("AZURE_SECRET_REF_PLACEHOLDER_NAME"))


def test_azure_vault_url_blocked_by_default():
    with pytest.raises(SecretRefError):
        validate_cloud_secret_ref(
            "https://example-placeholder.vault.azure.net",
            "azure_key_vault",
        )


@pytest.mark.parametrize("message", ["fake-auth-error", "fake-not-found", "fake-permission"])
def test_azure_errors_are_sanitized(monkeypatch, message):
    provider = azure_provider(monkeypatch, AzureClient(error=RuntimeError(message)))
    with pytest.raises(SecretProviderResolutionError) as error:
        provider.get_secret("AZURE_SECRET_REF_PLACEHOLDER_NAME")
    assert message not in str(error.value)


class GcpClient:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.calls = 0

    def access_secret_version(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(payload=SimpleNamespace(data=self.value))


def gcp_provider(monkeypatch, client):
    monkeypatch.setenv("GCP_PROJECT_ID", "example-project-placeholder")
    return GcpSecretManagerProvider(
        configured(
            secret_provider="gcp_secret_manager",
            secret_provider_allow_cloud=True,
            secret_provider_cloud_network_enabled=True,
            secret_provider_cloud_confirmation=CLOUD_CONFIRMATION_PHRASE,
            gcp_secret_manager_enabled=True,
        ),
        client=client,
    )


def test_gcp_mocked_resolution_is_internal_and_health_offline(monkeypatch):
    value = "must-not-appear-gcp-secret-value"
    client = GcpClient(value=value.encode())
    provider = gcp_provider(monkeypatch, client)
    provider.health_check(["GCP_SECRET_REF_PLACEHOLDER_NAME"])
    assert client.calls == 0
    assert provider.get_secret("GCP_SECRET_REF_PLACEHOLDER_NAME") == value


def test_gcp_full_resource_name_blocked_by_default():
    with pytest.raises(SecretRefError):
        validate_cloud_secret_ref(
            "projects/example-project-placeholder/secrets/fake-placeholder/versions/latest",
            "gcp_secret_manager",
        )


@pytest.mark.parametrize("message", ["fake-auth-error", "fake-not-found", "fake-permission"])
def test_gcp_errors_are_sanitized(monkeypatch, message):
    provider = gcp_provider(monkeypatch, GcpClient(error=RuntimeError(message)))
    with pytest.raises(SecretProviderResolutionError) as error:
        provider.get_secret("GCP_SECRET_REF_PLACEHOLDER_NAME")
    assert message not in str(error.value)


@pytest.mark.parametrize(
    "unsafe_ref",
    [
        '{"private_key":"fake-private-key-placeholder"}',
        "-----BEGIN PRIVATE KEY----- fake-placeholder",
        "Authorization: Bearer fake-placeholder",
        "postgresql://example:placeholder@database.invalid/example",
        "https://example.invalid/item?signature=fake-placeholder",
        "/home/example/.aws/credentials",
        "AWS_ACCESS_KEY_ID=fake-placeholder",
        "123456789012",
        "00000000-0000-0000-0000-000000000000",
    ],
)
def test_cloud_ref_validation_blocks_unsafe_material(unsafe_ref):
    with pytest.raises(SecretRefError) as error:
        validate_cloud_secret_ref(unsafe_ref, "aws_secrets_manager")
    assert unsafe_ref not in str(error.value)


@pytest.mark.parametrize(
    ("provider", "ref"),
    [
        ("aws_secrets_manager", "AWS_SECRET_REF_PLACEHOLDER_NAME"),
        ("azure_key_vault", "AZURE_SECRET_REF_PLACEHOLDER_NAME"),
        ("gcp_secret_manager", "GCP_SECRET_REF_PLACEHOLDER_NAME"),
    ],
)
def test_placeholder_cloud_refs_are_allowed(provider, ref):
    assert validate_cloud_secret_ref(ref, provider).name == ref


@pytest.mark.parametrize(
    "script",
    [
        "check_cloud_secret_provider.py",
        "print_cloud_secret_provider_template.py",
        "explain_cloud_secret_resolution.py",
    ],
)
def test_cloud_cli_is_offline_and_sanitized(script):
    marker = "must-not-appear-unrelated-cloud-value"
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "UNRELATED_PRIVATE_VALUE": marker},
    )
    assert result.returncode == 0, result.stderr
    assert marker not in result.stdout
    assert str(ROOT) not in result.stdout
    assert "arn:aws:" not in result.stdout.casefold()
    assert ".vault.azure.net" not in result.stdout.casefold()
    assert "projects/" not in result.stdout.casefold()


def test_makefile_quality_and_docs_cover_g1():
    makefile = (ROOT / "Makefile").read_text()
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in ("cloud-secret-template", "cloud-secret-check", "cloud-secret-explain"):
        assert f"{target}:" in makefile
        assert target in quality
    docs = (ROOT / "docs/cloud-secret-providers.md").read_text().casefold()
    assert "env" in docs and "file" in docs
    assert "optional" in docs and "disabled by default" in docs
    assert "never contact cloud" in docs
    for filename in (
        "aws_secret_refs.example.json",
        "azure_secret_refs.example.json",
        "gcp_secret_refs.example.json",
    ):
        contents = (ROOT / "examples/cloud-secret-providers" / filename).read_text()
        assert "PLACEHOLDER" in contents
        assert "secret_values_included" in contents
