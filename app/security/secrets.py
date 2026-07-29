import os
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
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


class SecretProviderConfigError(SecretProviderMisconfiguredError):
    """Provider configuration is unsafe or incomplete."""


class SecretProviderResolutionError(SecretProviderError):
    """A secret could not be resolved without exposing its value."""


class SecretProviderBlockedError(SecretProviderError):
    """A secret operation was blocked by a safety boundary."""


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
        if not self.settings.secret_provider_allow_env:
            raise SecretProviderBlockedError("Environment secret resolution is disabled.")
        variable_name = self._normalized(ref)
        value = os.getenv(variable_name)
        if value is None or not value.strip():
            raise SecretNotFoundError(
                f"Secret was not found for {mask_secret_ref(ref, self.settings)}."
            )
        return value

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        if not self.settings.secret_provider_allow_env:
            return SecretProviderHealth(
                provider=self.name,
                status="unavailable",
                checked_refs_count=len(required_refs or []),
                present_refs_count=0,
                missing_refs_count=len(required_refs or []),
                message="Environment secret resolution is disabled.",
            )
        return super().health_check(required_refs)


class FileSecretProvider(_ProviderBase):
    name = "file"
    blocked_suffixes = {
        ".db",
        ".sqlite",
        ".sqlite3",
        ".pdf",
        ".zip",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".docx",
        ".xlsx",
        ".json",
        ".log",
    }
    private_root_markers = {
        "private-workspace",
        "private-secrets",
        ".local-secrets",
        "secrets.local",
    }

    def _root(self) -> Path:
        root = self.settings.file_secret_root
        if root in {Path("."), Path("/")} or ".." in root.parts:
            raise SecretProviderConfigError("File secret root is unsafe.")
        if (
            self.settings.file_secret_require_private_root
            and not any(part in self.private_root_markers for part in root.parts)
        ):
            raise SecretProviderConfigError(
                "File secret root is not an approved private/ignored location."
            )
        return root.resolve()

    def _secret_path(self, ref: str) -> Path:
        if not self.settings.secret_provider_allow_file:
            raise SecretProviderBlockedError("File secret resolution is disabled.")
        candidate = Path(ref.strip())
        if (
            not self.settings.file_secret_allow_relative_refs
            or candidate.is_absolute()
            or ".." in candidate.parts
            or not candidate.parts
        ):
            raise SecretProviderBlockedError("File secret reference is unsafe.")
        if candidate.suffix.casefold() in self.blocked_suffixes:
            raise SecretProviderBlockedError("File secret type is not allowed.")
        root = self._root()
        target = (root / candidate).resolve()
        if root not in target.parents:
            raise SecretProviderBlockedError("File secret reference escaped its root.")
        return target

    def describe_ref(self, ref: str) -> dict[str, str]:
        self._secret_path(ref)
        candidate = Path(ref)
        safe_ref = candidate.name if candidate.is_absolute() else candidate.as_posix()
        visible = safe_ref[-4:] if len(safe_ref) > 4 else ""
        return {"provider": self.name, "masked_ref": f"file/********{visible}"}

    def get_secret(self, ref: str) -> str:
        target = self._secret_path(ref)
        try:
            if not target.is_file() or target.is_symlink():
                raise SecretNotFoundError("File secret is missing or is not a regular file.")
            size = target.stat().st_size
            if size <= 0 or size > self.settings.file_secret_max_bytes:
                raise SecretProviderBlockedError("File secret size is outside allowed bounds.")
            raw = target.read_bytes()
        except SecretProviderError:
            raise
        except OSError as exc:
            raise SecretProviderResolutionError(
                "File secret could not be read safely."
            ) from exc
        if b"\x00" in raw:
            raise SecretProviderBlockedError("Binary secret files are not allowed.")
        try:
            value = raw.decode("utf-8").rstrip("\r\n")
        except UnicodeDecodeError as exc:
            raise SecretProviderBlockedError(
                "Binary secret files are not allowed."
            ) from exc
        if not value:
            raise SecretNotFoundError("File secret is empty.")
        return value

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        refs = required_refs or []
        try:
            root = self._root()
        except SecretProviderError:
            return SecretProviderHealth(
                provider=self.name,
                status="unavailable",
                checked_refs_count=len(refs),
                present_refs_count=0,
                missing_refs_count=len(refs),
                message="File secret root is unsafe or misconfigured.",
            )
        if not root.is_dir():
            return SecretProviderHealth(
                provider=self.name,
                status="unavailable",
                checked_refs_count=len(refs),
                present_refs_count=0,
                missing_refs_count=len(refs),
                message="File secret root is missing or unavailable.",
            )
        results = [
            SecretRefHealth(
                masked_ref=self.describe_ref(ref)["masked_ref"],
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
            message="File provider health reports reference presence only.",
        )


class OptionalCloudSecretProvider(_ProviderBase):
    dependency = ""
    enabled_setting = ""

    def _enabled(self) -> bool:
        return bool(
            self.settings.secret_provider_allow_cloud
            and getattr(self.settings, self.enabled_setting)
        )

    def _dependency_present(self) -> bool:
        try:
            return find_spec(self.dependency) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def get_secret(self, ref: str) -> str:
        self._normalized(ref)
        if not self._enabled():
            raise SecretProviderBlockedError("Cloud secret provider is disabled.")
        if not self._dependency_present():
            raise SecretProviderUnavailableError(
                "Optional cloud secret provider dependency is missing."
            )
        raise SecretProviderConfigError(
            "Cloud secret provider requires private configuration verification."
        )

    def health_check(
        self, required_refs: list[str] | None = None
    ) -> SecretProviderHealth:
        enabled = self._enabled()
        dependency_present = self._dependency_present()
        status = (
            "dependency_missing"
            if enabled and not dependency_present
            else "unavailable"
        )
        return SecretProviderHealth(
            provider=self.name,
            status=status,
            checked_refs_count=len(required_refs or []),
            present_refs_count=0,
            missing_refs_count=len(required_refs or []),
            refs=[
                SecretRefHealth(
                    masked_ref=mask_secret_ref(ref, self.settings),
                    status="unknown",
                )
                for ref in (required_refs or [])
            ],
            message="Cloud provider health is configuration-only; no external call was made.",
        )


class AwsSecretsManagerProvider(OptionalCloudSecretProvider):
    name = "aws_secrets_manager"
    dependency = "boto3"
    enabled_setting = "aws_secrets_enabled"


class AzureKeyVaultProvider(OptionalCloudSecretProvider):
    name = "azure_key_vault"
    dependency = "azure.keyvault.secrets"
    enabled_setting = "azure_key_vault_enabled"


class GcpSecretManagerProvider(OptionalCloudSecretProvider):
    name = "gcp_secret_manager"
    dependency = "google.cloud.secretmanager"
    enabled_setting = "gcp_secret_manager_enabled"


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
    "FileSecretProvider",
    "ExternalPlaceholderSecretProvider",
    "AwsSecretsManagerProvider",
    "AzureKeyVaultProvider",
    "GcpSecretManagerProvider",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretProviderError",
    "SecretProviderHealth",
    "SecretProviderBlockedError",
    "SecretProviderConfigError",
    "SecretProviderMisconfiguredError",
    "SecretProviderResolutionError",
    "SecretProviderUnavailableError",
    "TestSecretProvider",
]
