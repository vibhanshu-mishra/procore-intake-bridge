import re
from importlib.util import find_spec
from pathlib import Path, PurePosixPath

from app.config import Settings
from app.schemas.storage import (
    StorageDeleteResult,
    StorageInventoryItem,
    StorageListResult,
    StorageObjectStatus,
    StorageProviderFinding,
    StorageProviderHealth,
    StorageProviderKind,
    StorageProviderReadiness,
    StorageReadResult,
    StorageWriteResult,
)
from app.services.attachment_storage_keys import (
    AttachmentStorageKeyError,
    mask_storage_key,
    normalize_storage_key,
)
from app.services.attachment_storage_keys import validate_storage_key as _validate_key
from app.services.attachment_storage_provider import (
    AttachmentStorageBlockedError,
    AttachmentStorageObjectNotFoundError,
    LocalAttachmentStorageProvider,
    TestAttachmentStorageProvider,
)

SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
DATABASE_URL = re.compile(r"(?i)(?:sqlite|postgres(?:ql)?|mysql|mongodb)://")
CLOUD_CREDENTIAL = re.compile(
    r"(?i)(?:aws_access_key|secret_access_key|client_secret|private_key)\s*[:=]"
)
BLOCKED_SUFFIXES = {
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
}
PRIVATE_OUTPUT = re.compile(
    r"(?i)(private-evidence|pilot-approval|support-bundle|smoke-report|"
    r"webhook-report|storage-report|storage-manifest)"
)
PRIVATE_ROOT_MARKERS = {
    "private-workspace",
    "private-storage",
    ".local-storage",
    "storage.local",
    "attachment-storage",
    "object-storage",
}


class StorageProviderError(RuntimeError):
    """Storage failed without exposing contents, keys, or private paths."""


class StorageProviderConfigError(StorageProviderError):
    pass


class StorageProviderOperationError(StorageProviderError):
    pass


class StorageProviderBlockedError(StorageProviderError):
    pass


def validate_storage_key(key: str, settings: Settings | None = None) -> str:
    value = str(key)
    if (
        SIGNED_URL.search(value)
        or DATABASE_URL.search(value)
        or CLOUD_CREDENTIAL.search(value)
        or PRIVATE_OUTPUT.search(value)
    ):
        raise StorageProviderBlockedError("Storage key resembles unsafe private material.")
    try:
        normalized = _validate_key(value)
    except AttachmentStorageKeyError as exc:
        raise StorageProviderBlockedError("Storage key is unsafe.") from exc
    if PurePosixPath(normalized).suffix.casefold() in BLOCKED_SUFFIXES:
        raise StorageProviderBlockedError("Storage object type is blocked.")
    return normalized


def mask_storage_ref(ref: str) -> str:
    return mask_storage_key(ref)


def assert_storage_value_never_reported(value) -> None:
    if value not in (None, b"", ""):
        raise StorageProviderBlockedError(
            "Storage contents and private paths cannot be included in reports."
        )


class LocalStorageProvider:
    name = "local"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = self._safe_root()
        adapted = settings.model_copy(
            update={
                "attachment_storage_root": self.root,
                "attachment_storage_max_object_bytes": settings.local_storage_max_bytes,
                "attachment_storage_write_metadata_only": False,
                "attachment_storage_require_safe_keys": True,
                "attachment_allow_overwrite": settings.local_storage_overwrite,
            }
        )
        self.backend = LocalAttachmentStorageProvider(adapted)

    def _safe_root(self) -> Path:
        root = self.settings.local_storage_root
        if root in {Path("."), Path("/")} or ".." in root.parts:
            raise StorageProviderConfigError("Local storage root is unsafe.")
        if root.is_absolute() and not self.settings.local_storage_allow_absolute_root:
            raise StorageProviderConfigError("Absolute local storage roots are disabled.")
        if (
            self.settings.local_storage_require_private_root
            and not any(part in PRIVATE_ROOT_MARKERS for part in root.parts)
        ):
            raise StorageProviderConfigError(
                "Local storage root is not an approved private/ignored location."
            )
        if not self.settings.storage_provider_allow_local:
            raise StorageProviderBlockedError("Local storage provider is disabled.")
        return root.resolve()

    def _key(self, key: str) -> str:
        normalized = validate_storage_key(key, self.settings)
        allowed = {
            item.strip().casefold()
            for item in self.settings.local_storage_allowed_extensions.split(",")
            if item.strip()
        }
        if allowed and PurePosixPath(normalized).suffix.casefold() not in allowed:
            raise StorageProviderBlockedError("Storage object extension is not allowed.")
        return normalized

    def _validate_content(self, data: bytes) -> None:
        if len(data) > self.settings.local_storage_max_bytes:
            raise StorageProviderBlockedError("Storage object exceeds the size limit.")
        if self.settings.local_storage_block_binary:
            if b"\x00" in data:
                raise StorageProviderBlockedError("Binary storage objects are blocked.")
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise StorageProviderBlockedError(
                    "Binary storage objects are blocked."
                ) from exc

    def write(self, key: str, data: bytes) -> StorageWriteResult:
        safe = self._key(key)
        self._validate_content(data)
        try:
            result = self.backend.write_bytes(
                safe,
                data,
                overwrite=self.settings.local_storage_overwrite,
            )
        except AttachmentStorageBlockedError as exc:
            raise StorageProviderBlockedError(
                "Local storage write was blocked; details were suppressed."
            ) from exc
        return StorageWriteResult(
            provider=self.name,
            masked_ref=mask_storage_ref(safe),
            written=True,
            size_bytes=result.size_bytes,
        )

    def read(self, key: str) -> bytes:
        safe = self._key(key)
        try:
            result = self.backend.read_bytes(safe)
        except AttachmentStorageObjectNotFoundError as exc:
            raise StorageProviderOperationError("Storage object was not found.") from exc
        except AttachmentStorageBlockedError as exc:
            raise StorageProviderBlockedError(
                "Local storage read was blocked; details were suppressed."
            ) from exc
        self._validate_content(result.data)
        return result.data

    def read_result(self, key: str) -> StorageReadResult:
        safe = self._key(key)
        data = self.read(safe)
        return StorageReadResult(
            provider=self.name,
            masked_ref=mask_storage_ref(safe),
            found=True,
            size_bytes=len(data),
        )

    def exists(self, key: str) -> bool:
        try:
            return self.backend.exists(self._key(key))
        except AttachmentStorageBlockedError as exc:
            raise StorageProviderBlockedError(
                "Local storage lookup was blocked; details were suppressed."
            ) from exc

    def delete(self, key: str) -> StorageDeleteResult:
        safe = self._key(key)
        try:
            deleted = self.backend.delete(safe)
        except AttachmentStorageBlockedError as exc:
            raise StorageProviderBlockedError(
                "Local storage delete was blocked; details were suppressed."
            ) from exc
        return StorageDeleteResult(
            provider=self.name, masked_ref=mask_storage_ref(safe), deleted=deleted
        )

    def list(self) -> StorageListResult:
        try:
            objects = self.backend.list_objects()
        except AttachmentStorageBlockedError as exc:
            raise StorageProviderBlockedError(
                "Local storage inventory was blocked; details were suppressed."
            ) from exc
        items = [
            StorageInventoryItem(
                masked_ref=item["storage_key"],
                status=StorageObjectStatus.PRESENT,
                size_bytes=item["size_bytes"],
            )
            for item in objects
        ]
        return StorageListResult(provider=self.name, items=items)

    def health(self) -> StorageProviderHealth:
        return StorageProviderHealth(
            provider=self.name,
            status="healthy",
            configured=True,
            available=True,
        )


class TestStorageProvider(LocalStorageProvider):
    name = "test"

    def __init__(self, settings: Settings):
        self.settings = settings
        adapted = settings.model_copy(
            update={
                "attachment_storage_max_object_bytes": settings.local_storage_max_bytes,
                "attachment_allow_overwrite": settings.local_storage_overwrite,
            }
        )
        self.backend = TestAttachmentStorageProvider(adapted)
        self.root = Path("test-storage")

    def health(self) -> StorageProviderHealth:
        return StorageProviderHealth(
            provider="test", status="healthy", configured=True, available=True
        )


class DisabledStorageProvider:
    name = "disabled"

    def _blocked(self, *args, **kwargs):
        raise StorageProviderBlockedError("Storage provider is disabled.")

    write = read = read_result = exists = delete = list = _blocked

    def health(self) -> StorageProviderHealth:
        return StorageProviderHealth(
            provider="disabled",
            status="disabled",
            configured=False,
            available=False,
        )


class ExternalPlaceholderStorageProvider(DisabledStorageProvider):
    name = "external_placeholder"

    def _blocked(self, *args, **kwargs):
        raise StorageProviderOperationError(
            "External placeholder storage is unavailable."
        )

    write = read = read_result = exists = delete = list = _blocked

    def health(self) -> StorageProviderHealth:
        return StorageProviderHealth(
            provider="external_placeholder",
            status="unavailable",
            configured=False,
            available=False,
        )


class OptionalCloudStorageProvider(ExternalPlaceholderStorageProvider):
    dependency = ""
    enabled_setting = ""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _dependency_present(self) -> bool:
        try:
            return find_spec(self.dependency) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def _enabled(self) -> bool:
        return bool(
            self.settings.storage_provider_allow_cloud
            and getattr(self.settings, self.enabled_setting)
        )

    def _blocked(self, *args, **kwargs):
        if not self._enabled():
            raise StorageProviderBlockedError("Cloud storage provider is disabled.")
        if not self._dependency_present():
            raise StorageProviderOperationError(
                "Optional cloud storage dependency is missing."
            )
        raise StorageProviderConfigError(
            "Cloud storage requires private configuration verification."
        )

    write = read = read_result = exists = delete = list = _blocked

    def health(self) -> StorageProviderHealth:
        enabled = self._enabled()
        missing = enabled and not self._dependency_present()
        return StorageProviderHealth(
            provider=StorageProviderKind(self.name),
            status="dependency_missing" if missing else "unavailable",
            configured=enabled,
            available=False,
            dependency_missing=missing,
            permission_unknown=enabled and not missing,
            external_calls=False,
        )


class S3StorageProvider(OptionalCloudStorageProvider):
    name = "s3"
    dependency = "boto3"
    enabled_setting = "s3_storage_enabled"


class AzureBlobStorageProvider(OptionalCloudStorageProvider):
    name = "azure_blob"
    dependency = "azure.storage.blob"
    enabled_setting = "azure_blob_storage_enabled"


class GcsStorageProvider(OptionalCloudStorageProvider):
    name = "gcs"
    dependency = "google.cloud.storage"
    enabled_setting = "gcs_storage_enabled"


def build_storage_provider(kind: str, settings: Settings):
    selected = StorageProviderKind(kind)
    if selected == StorageProviderKind.LOCAL:
        return LocalStorageProvider(settings)
    if selected == StorageProviderKind.TEST:
        if settings.environment != "local":
            raise StorageProviderConfigError("Test storage is local-only.")
        return TestStorageProvider(settings)
    if selected == StorageProviderKind.DISABLED:
        return DisabledStorageProvider()
    if selected == StorageProviderKind.EXTERNAL_PLACEHOLDER:
        return ExternalPlaceholderStorageProvider()
    cloud = {
        StorageProviderKind.S3: S3StorageProvider,
        StorageProviderKind.AZURE_BLOB: AzureBlobStorageProvider,
        StorageProviderKind.GCS: GcsStorageProvider,
    }
    return cloud[selected](settings)


def build_storage_provider_health(settings: Settings) -> StorageProviderHealth:
    try:
        return build_storage_provider(settings.storage_provider, settings).health()
    except (StorageProviderError, ValueError):
        return StorageProviderHealth(
            provider=StorageProviderKind(settings.storage_provider),
            status="unavailable",
            configured=True,
            available=False,
        )


def build_storage_provider_readiness(settings: Settings) -> StorageProviderReadiness:
    health = build_storage_provider_health(settings)
    ready = health.available
    return StorageProviderReadiness(
        provider=health.provider,
        ready=ready,
        health=health,
        findings=[
            StorageProviderFinding(
                code="storage_posture",
                severity="info" if ready else "warning",
                message=(
                    "Storage provider is available without exposing contents or paths."
                    if ready
                    else "Storage provider is unavailable or needs private configuration."
                ),
            )
        ],
    )


def collect_required_storage_refs(settings: Settings) -> list[StorageInventoryItem]:
    configured = bool(settings.attachment_storage_external_bucket_ref)
    return (
        [
            StorageInventoryItem(
                masked_ref="object-config-********",
                status=StorageObjectStatus.OPERATION_NOT_ATTEMPTED,
            )
        ]
        if configured
        else []
    )


def validate_required_storage_refs(settings: Settings) -> list[StorageInventoryItem]:
    return collect_required_storage_refs(settings)


__all__ = [
    "AzureBlobStorageProvider",
    "DisabledStorageProvider",
    "ExternalPlaceholderStorageProvider",
    "GcsStorageProvider",
    "LocalStorageProvider",
    "S3StorageProvider",
    "StorageProviderBlockedError",
    "StorageProviderConfigError",
    "StorageProviderError",
    "StorageProviderOperationError",
    "TestStorageProvider",
    "assert_storage_value_never_reported",
    "build_storage_provider",
    "build_storage_provider_health",
    "build_storage_provider_readiness",
    "collect_required_storage_refs",
    "mask_storage_ref",
    "normalize_storage_key",
    "validate_required_storage_refs",
    "validate_storage_key",
]
