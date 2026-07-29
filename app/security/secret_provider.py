"""Backward-compatible exports for the B2 provider layer."""

import re

from app.config import Settings
from app.security.secret_provider_factory import build_secret_provider
from app.security.secrets import (
    DisabledSecretProvider,
    EnvSecretProvider,
    ExternalPlaceholderSecretProvider,
    FileSecretProvider,
    SecretNotFoundError,
    SecretProvider,
    SecretProviderError,
    SecretProviderHealth,
    SecretProviderMisconfiguredError,
    SecretProviderUnavailableError,
    TestSecretProvider,
)

SECRET_ENV_PREFIX = "PROCORE_INTAKE_SECRET_"


def secret_name_to_env_var(secret_name: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", secret_name.strip().upper()).strip("_")
    if not normalized:
        raise SecretNotFoundError("Secret reference is empty or invalid.")
    if normalized.startswith(SECRET_ENV_PREFIX):
        return normalized
    return f"{SECRET_ENV_PREFIX}{normalized}"


def get_secret_provider(settings: Settings) -> SecretProvider:
    return build_secret_provider(settings)


__all__ = [
    "DisabledSecretProvider",
    "EnvSecretProvider",
    "FileSecretProvider",
    "ExternalPlaceholderSecretProvider",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretProviderError",
    "SecretProviderHealth",
    "SecretProviderMisconfiguredError",
    "SecretProviderUnavailableError",
    "TestSecretProvider",
    "get_secret_provider",
    "secret_name_to_env_var",
]
