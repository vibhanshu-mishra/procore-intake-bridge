import os
import re
from typing import Protocol

from app.config import Settings

SECRET_ENV_PREFIX = "PROCORE_INTAKE_SECRET_"


class SecretNotFoundError(LookupError):
    """A secret reference could not be resolved without revealing any secret value."""


class SecretProvider(Protocol):
    def get_secret(self, secret_name: str) -> str:
        """Resolve an opaque secret reference."""


def secret_name_to_env_var(secret_name: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", secret_name.strip().upper()).strip("_")
    if not normalized:
        raise SecretNotFoundError("The secret reference is empty or invalid.")
    return f"{SECRET_ENV_PREFIX}{normalized}"


class EnvSecretProvider:
    """Resolve local-development secrets from a deterministic environment mapping."""

    def get_secret(self, secret_name: str) -> str:
        variable_name = secret_name_to_env_var(secret_name)
        value = os.getenv(variable_name)
        if value is None or not value.strip():
            raise SecretNotFoundError(
                f"Secret reference {secret_name!r} was not found in {variable_name}."
            )
        return value


def get_secret_provider(settings: Settings) -> SecretProvider:
    if settings.secret_provider == "env":
        return EnvSecretProvider()
    raise ValueError("Unsupported secret provider configuration.")
