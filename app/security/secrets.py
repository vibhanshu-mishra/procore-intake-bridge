import os
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.config import Settings
from app.security.secret_refs import (
    SecretRefError,
    mask_secret_ref,
    normalize_secret_ref,
)


class SecretProviderError(RuntimeError):
    """Base provider error whose message never contains a credential value."""


class SecretNotFoundError(SecretProviderError, LookupError):
    """A reference could not be resolved."""


class SecretProviderUnavailableError(SecretProviderError):
    """The selected provider is unavailable."""


class SecretProviderMisconfiguredError(SecretProviderError):
    """The selected provider or reference is misconfigured."""


@dataclass(frozen=True)
class SecretRefHealth:
    masked_ref: str
    status: Literal["present", "missing", "unknown"]


@dataclass(frozen=True)
class SecretProviderHealth:
    provider: str
    status: Literal["healthy", "degraded", "disabled", "unavailable"]
    checked_refs_count: int
    present_refs_count: int
    missing_refs_count: int
    refs: list[SecretRefHealth] = field(default_factory=list)
    message: str = ""


class SecretProvider(Protocol):
    name: str

    def get_secret(self, ref: str) -> str: ...

    def has_secret(self, ref: str) -> bool: ...

    def describe_ref(self, ref: str) -> dict[str, str]: ...

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth: ...


class _ProviderBase:
    name = "base"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings(_env_file=None)

    def _normalized(self, ref: str) -> str:
        try:
            return normalize_secret_ref(ref, self.settings).name
        except SecretRefError as exc:
            raise SecretProviderMisconfiguredError(
                "Secret reference is invalid or missing its required prefix."
            ) from exc

    def describe_ref(self, ref: str) -> dict[str, str]:
        return {
            "provider": self.name,
            "masked_ref": mask_secret_ref(ref, self.settings),
        }

    def has_secret(self, ref: str) -> bool:
        try:
            self.get_secret(ref)
        except SecretProviderError:
            return False
        return True

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        refs = required_refs or []
        results = [
            SecretRefHealth(
                masked_ref=mask_secret_ref(ref, self.settings),
                status="present" if self.has_secret(ref) else "missing",
            )
            for ref in refs
        ]
        missing = sum(item.status == "missing" for item in results)
        return SecretProviderHealth(
            provider=self.name,
            status="healthy" if missing == 0 else "degraded",
            checked_refs_count=len(results),
            present_refs_count=len(results) - missing,
            missing_refs_count=missing,
            refs=results,
            message="Provider health reports reference presence only.",
        )


class EnvSecretProvider(_ProviderBase):
    name = "env"

    def get_secret(self, ref: str) -> str:
        variable_name = self._normalized(ref)
        value = os.getenv(variable_name)
        if value is None or not value.strip():
            raise SecretNotFoundError(
                f"Secret was not found for {mask_secret_ref(ref, self.settings)}."
            )
        return value


class TestSecretProvider(_ProviderBase):
    name = "test"
    __test__ = False

    def __init__(self, secrets: dict[str, str], settings: Settings | None = None):
        super().__init__(settings)
        self._secrets = {
            self._normalized(ref): value for ref, value in secrets.items()
        }

    def get_secret(self, ref: str) -> str:
        value = self._secrets.get(self._normalized(ref))
        if value is None:
            raise SecretNotFoundError(
                f"Test secret was not found for {mask_secret_ref(ref, self.settings)}."
            )
        return value


class DisabledSecretProvider(_ProviderBase):
    name = "disabled"

    def get_secret(self, ref: str) -> str:
        self._normalized(ref)
        raise SecretProviderUnavailableError("Secret provider is disabled.")

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        return SecretProviderHealth(
            provider=self.name,
            status="disabled",
            checked_refs_count=len(required_refs or []),
            present_refs_count=0,
            missing_refs_count=len(required_refs or []),
            message="Secret resolution is disabled and fails closed.",
        )


class ExternalPlaceholderSecretProvider(_ProviderBase):
    name = "external_placeholder"

    def get_secret(self, ref: str) -> str:
        self._normalized(ref)
        raise SecretProviderUnavailableError(
            "External secret provider adapter is not implemented."
        )

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        return SecretProviderHealth(
            provider=self.name,
            status="unavailable",
            checked_refs_count=len(required_refs or []),
            present_refs_count=0,
            missing_refs_count=len(required_refs or []),
            message="External placeholder performs no network calls.",
        )


__all__ = [
    "DisabledSecretProvider",
    "EnvSecretProvider",
    "ExternalPlaceholderSecretProvider",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretProviderError",
    "SecretProviderHealth",
    "SecretProviderMisconfiguredError",
    "SecretProviderUnavailableError",
    "TestSecretProvider",
]
