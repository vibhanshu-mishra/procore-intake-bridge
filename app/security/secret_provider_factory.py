from typing import Any

from app.config import Settings
from app.security.secrets import (
    AwsSecretsManagerProvider,
    AzureKeyVaultProvider,
    DisabledSecretProvider,
    EnvSecretProvider,
    ExternalPlaceholderSecretProvider,
    FileSecretProvider,
    GcpSecretManagerProvider,
    SecretProvider,
    SecretProviderMisconfiguredError,
    TestSecretProvider,
)


def get_secret_provider_name(settings: Settings) -> str:
    return settings.secret_provider


def build_secret_provider(
    settings: Settings, test_secrets: dict[str, str] | None = None
) -> SecretProvider:
    if settings.secret_provider == "env":
        return EnvSecretProvider(settings)
    if settings.secret_provider == "file":
        return FileSecretProvider(settings)
    if settings.secret_provider == "disabled":
        return DisabledSecretProvider(settings)
    if settings.secret_provider == "external_placeholder":
        return ExternalPlaceholderSecretProvider(settings)
    if settings.secret_provider == "aws_secrets_manager":
        return AwsSecretsManagerProvider(settings)
    if settings.secret_provider == "azure_key_vault":
        return AzureKeyVaultProvider(settings)
    if settings.secret_provider == "gcp_secret_manager":
        return GcpSecretManagerProvider(settings)
    if settings.secret_provider == "test":
        if settings.environment != "local" or test_secrets is None:
            raise SecretProviderMisconfiguredError(
                "Test secret provider requires local mode and injected test values."
            )
        return TestSecretProvider(test_secrets, settings)
    raise SecretProviderMisconfiguredError("Unknown secret provider fails closed.")


def summarize_secret_provider_config(settings: Settings) -> dict[str, Any]:
    return {
        "provider": get_secret_provider_name(settings),
        "health_check_enabled": settings.secret_health_check_enabled,
        "fail_closed": settings.secret_fail_closed,
        "reference_prefix_configured": bool(settings.secret_ref_prefix),
        "reference_prefix_required": settings.secret_require_prefix,
        "mask_mode": settings.secret_mask_mode,
        "external_provider_name_configured": bool(
            settings.external_secret_provider_name.strip()
        ),
        "external_region_configured": bool(
            settings.external_secret_provider_region.strip()
        ),
        "external_project_configured": bool(
            settings.external_secret_provider_project.strip()
        ),
        "external_vault_url_configured": bool(
            settings.external_secret_provider_vault_url.strip()
        ),
        "external_adapter_implemented": False,
        "strict_redaction": settings.secret_provider_strict_redaction,
        "env_allowed": settings.secret_provider_allow_env,
        "file_allowed": settings.secret_provider_allow_file,
        "cloud_allowed": settings.secret_provider_allow_cloud,
        "file_root_configured": bool(settings.file_secret_root.parts),
        "file_root_is_absolute": settings.file_secret_root.is_absolute(),
        "file_max_bytes": settings.file_secret_max_bytes,
        "aws_enabled": settings.aws_secrets_enabled,
        "azure_enabled": settings.azure_key_vault_enabled,
        "gcp_enabled": settings.gcp_secret_manager_enabled,
        "external_calls": False,
        "values_exposed": False,
    }
