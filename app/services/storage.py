import os
import re
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path, PurePosixPath

from app.config import Settings
from app.schemas.storage import (
    CloudStorageProviderFinding,
    CloudStorageProviderHealth,
    CloudStorageProviderKind,
    CloudStorageProviderStatus,
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
CLOUD_STORAGE_CONFIRMATION_PHRASE = (
    "I understand this may contact an external cloud storage provider"
)
S3_RESOURCE = re.compile(r"(?i)^(?:s3://|arn:aws[a-z-]*:s3:)")
AZURE_BLOB_RESOURCE = re.compile(
    r"(?i)^https://[a-z0-9-]+\.blob\.core\.windows\.net/"
)
GCS_RESOURCE = re.compile(r"(?i)^(?:gs://|projects/[^/]+/(?:buckets|locations)/)")
UNSAFE_CLOUD_STORAGE_REF = re.compile(
    r"(?is)(BEGIN [A-Z ]*PRIVATE KEY|"
    r'"(?:private_key|private_key_id|client_email|client_id)"\s*:|'
    r"(?:authorization|bearer|aws_access_key_id|aws_secret_access_key)|"
    r"(?:sqlite|postgres(?:ql)?|mysql|mongodb)://|"
    r"https?://\S+[?&](?:signature|signed|token|expires)=|"
    r"(?:^|/)\.(?:aws|azure|config/gcloud)(?:/|$)|"
    r"^[A-F0-9-]{32,36}$|^\d{12}$)"
)


class StorageProviderError(RuntimeError):
    """Storage failed without exposing contents, keys, or private paths."""


class StorageProviderConfigError(StorageProviderError):
    pass


class StorageProviderOperationError(StorageProviderError):
    pass


class StorageProviderBlockedError(StorageProviderConfigError):
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


def validate_cloud_storage_ref(
    value: str,
    provider: str,
    *,
    allow_s3_resource: bool = False,
    allow_azure_url: bool = False,
    allow_gcs_resource: bool = False,
) -> str:
    candidate = value.strip()
    if not candidate or UNSAFE_CLOUD_STORAGE_REF.search(candidate):
        raise StorageProviderBlockedError("Cloud storage reference is unsafe.")
    if S3_RESOURCE.match(candidate) and not allow_s3_resource:
        raise StorageProviderBlockedError("S3 resource identifiers are disabled.")
    if AZURE_BLOB_RESOURCE.match(candidate) and not allow_azure_url:
        raise StorageProviderBlockedError("Azure Blob URLs are disabled.")
    if GCS_RESOURCE.match(candidate) and not allow_gcs_resource:
        raise StorageProviderBlockedError("GCS resource identifiers are disabled.")
    if any(character.isspace() for character in candidate) or "=" in candidate:
        raise StorageProviderBlockedError("Cloud storage reference resembles inline data.")
    if provider not in {"s3", "azure_blob", "gcs"}:
        raise StorageProviderBlockedError("Cloud storage provider is unsupported.")
    return candidate


def mask_storage_ref(ref: str) -> str:
    return mask_storage_key(ref)


def assert_storage_value_never_reported(value) -> None:
    if value not in (None, b"", ""):
        raise StorageProviderBlockedError(
            "Storage contents and private paths cannot be included in reports."
        )


def _is_not_found_exception(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = str(response.get("Error", {}).get("Code", "")).casefold()
        if code in {"404", "nosuchkey", "notfound", "blobnotfound"}:
            return True
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    return status == 404 or code == 404


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

    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self._client = client

    def _dependency_present(self) -> bool:
        if self._client is not None:
            return True
        try:
            return find_spec(self.dependency) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def _enabled(self) -> bool:
        return bool(
            self.settings.storage_provider == self.name
            and self.settings.storage_provider_allow_cloud
            and getattr(self.settings, self.enabled_setting)
        )

    def _confirmation_present(self) -> bool:
        return (
            self.settings.storage_provider_cloud_confirmation
            == CLOUD_STORAGE_CONFIRMATION_PHRASE
        )

    def _config_ready(self) -> bool:
        return True

    def _assert_operations_allowed(self) -> None:
        if not self._enabled():
            raise StorageProviderBlockedError("Cloud storage provider is disabled.")
        if not self.settings.storage_provider_cloud_network_enabled:
            raise StorageProviderBlockedError("Cloud storage network access is disabled.")
        if not self._confirmation_present():
            raise StorageProviderBlockedError("Cloud storage confirmation is missing.")
        if not self._config_ready():
            raise StorageProviderConfigError(
                "Cloud storage needs private configuration references."
            )
        if not self._dependency_present():
            raise StorageProviderOperationError(
                "Optional cloud storage dependency is missing."
            )

    def _safe_key(self, key: str) -> str:
        return validate_storage_key(key, self.settings)

    def _full_key(self, key: str) -> str:
        return self._safe_key(key)

    def _write(self, key: str, data: bytes) -> None:
        raise NotImplementedError

    def _read(self, key: str) -> bytes:
        raise NotImplementedError

    def _exists(self, key: str) -> bool:
        raise NotImplementedError

    def _delete(self, key: str) -> None:
        raise NotImplementedError

    def _list(self) -> list[tuple[str, int | None]]:
        raise NotImplementedError

    def _operation(self, callback, message: str):
        self._assert_operations_allowed()
        try:
            return callback()
        except StorageProviderError:
            raise
        except Exception as exc:
            raise StorageProviderOperationError(message) from exc

    def write(self, key: str, data: bytes) -> StorageWriteResult:
        safe = self._safe_key(key)
        if not isinstance(data, bytes) or not data:
            raise StorageProviderBlockedError("Cloud storage writes require non-empty bytes.")
        if len(data) > self.settings.local_storage_max_bytes:
            raise StorageProviderBlockedError("Cloud storage object exceeds the size limit.")
        full_key = self._full_key(safe)
        self._operation(
            lambda: self._write(full_key, data),
            "Cloud storage write failed; provider details were suppressed.",
        )
        return StorageWriteResult(
            provider=StorageProviderKind(self.name),
            masked_ref=mask_storage_ref(safe),
            written=True,
            size_bytes=len(data),
        )

    def read(self, key: str) -> bytes:
        safe = self._safe_key(key)
        data = self._operation(
            lambda: self._read(self._full_key(safe)),
            "Cloud storage read failed; provider details were suppressed.",
        )
        if not isinstance(data, bytes) or len(data) > self.settings.local_storage_max_bytes:
            raise StorageProviderBlockedError(
                "Cloud storage result was not safe bounded bytes."
            )
        return data

    def read_result(self, key: str) -> StorageReadResult:
        safe = self._safe_key(key)
        data = self.read(safe)
        return StorageReadResult(
            provider=StorageProviderKind(self.name),
            masked_ref=mask_storage_ref(safe),
            found=True,
            size_bytes=len(data),
        )

    def exists(self, key: str) -> bool:
        safe = self._safe_key(key)
        return bool(
            self._operation(
                lambda: self._exists(self._full_key(safe)),
                "Cloud storage lookup failed; provider details were suppressed.",
            )
        )

    def delete(self, key: str) -> StorageDeleteResult:
        if not self.settings.storage_provider_cloud_allow_delete:
            raise StorageProviderBlockedError("Cloud storage delete is disabled.")
        safe = self._safe_key(key)
        self._operation(
            lambda: self._delete(self._full_key(safe)),
            "Cloud storage delete failed; provider details were suppressed.",
        )
        return StorageDeleteResult(
            provider=StorageProviderKind(self.name),
            masked_ref=mask_storage_ref(safe),
            deleted=True,
        )

    def list(self) -> StorageListResult:
        if not self.settings.storage_provider_cloud_allow_list:
            raise StorageProviderBlockedError("Cloud storage listing is disabled.")
        objects = self._operation(
            self._list,
            "Cloud storage listing failed; provider details were suppressed.",
        )
        return StorageListResult(
            provider=StorageProviderKind(self.name),
            items=[
                StorageInventoryItem(
                    masked_ref=mask_storage_ref(key),
                    status=StorageObjectStatus.PRESENT,
                    size_bytes=size,
                )
                for key, size in objects
            ],
        )

    def health(self) -> StorageProviderHealth:
        enabled = self._enabled()
        dependency_available = self._dependency_present()
        missing = enabled and not dependency_available
        configured = self._config_ready()
        return StorageProviderHealth(
            provider=StorageProviderKind(self.name),
            status="dependency_missing" if missing else "unavailable",
            configured=enabled and configured,
            available=False,
            dependency_missing=missing,
            permission_unknown=enabled and not missing and configured,
            external_calls=False,
        )


class S3StorageProvider(OptionalCloudStorageProvider):
    name = "s3"
    dependency = "boto3"
    enabled_setting = "s3_storage_enabled"

    def _config_ready(self) -> bool:
        region_ready = not self.settings.s3_require_region or bool(
            self.settings.s3_region_ref
            and os.getenv(self.settings.s3_region_ref, "").strip()
        )
        return region_ready and bool(
            self.settings.s3_bucket_ref
            and os.getenv(self.settings.s3_bucket_ref, "").strip()
        )

    def _bucket(self) -> str:
        return validate_cloud_storage_ref(
            os.getenv(self.settings.s3_bucket_ref, ""),
            self.name,
            allow_s3_resource=(
                self.settings.s3_allow_bucket_arns or self.settings.s3_allow_s3_urls
            ),
        )

    def _full_key(self, key: str) -> str:
        prefix = validate_storage_key(self.settings.s3_key_prefix)
        return f"{prefix}/{super()._full_key(key)}"

    def _storage_client(self):
        if self._client is not None:
            return self._client
        boto3 = import_module("boto3")
        config_type = import_module("botocore.config").Config
        return boto3.client(
            "s3",
            region_name=os.getenv(self.settings.s3_region_ref) or None,
            config=config_type(
                connect_timeout=self.settings.storage_provider_cloud_timeout_seconds,
                read_timeout=self.settings.storage_provider_cloud_timeout_seconds,
            ),
        )

    def _write(self, key: str, data: bytes) -> None:
        kwargs = {"Bucket": self._bucket(), "Key": key, "Body": data}
        if not self.settings.storage_provider_cloud_allow_overwrite:
            kwargs["IfNoneMatch"] = "*"
        self._storage_client().put_object(**kwargs)

    def _read(self, key: str) -> bytes:
        result = self._storage_client().get_object(Bucket=self._bucket(), Key=key)
        body = result.get("Body")
        return body.read() if hasattr(body, "read") else b""

    def _exists(self, key: str) -> bool:
        try:
            self._storage_client().head_object(Bucket=self._bucket(), Key=key)
        except Exception as exc:
            if _is_not_found_exception(exc):
                return False
            raise
        return True

    def _delete(self, key: str) -> None:
        self._storage_client().delete_object(Bucket=self._bucket(), Key=key)

    def _list(self) -> list[tuple[str, int | None]]:
        result = self._storage_client().list_objects_v2(
            Bucket=self._bucket(), Prefix=f"{self.settings.s3_key_prefix}/"
        )
        return [
            (str(item.get("Key", "")), item.get("Size"))
            for item in result.get("Contents", [])
        ]


class AzureBlobStorageProvider(OptionalCloudStorageProvider):
    name = "azure_blob"
    dependency = "azure.storage.blob"
    enabled_setting = "azure_blob_storage_enabled"

    def _config_ready(self) -> bool:
        return bool(
            self.settings.azure_blob_use_default_credential
            and self.settings.azure_storage_account_ref
            and os.getenv(self.settings.azure_storage_account_ref, "").strip()
            and self.settings.azure_blob_container_ref
            and os.getenv(self.settings.azure_blob_container_ref, "").strip()
        )

    def _container(self) -> str:
        return validate_cloud_storage_ref(
            os.getenv(self.settings.azure_blob_container_ref, ""),
            self.name,
            allow_azure_url=self.settings.azure_blob_allow_urls,
        )

    def _full_key(self, key: str) -> str:
        prefix = validate_storage_key(self.settings.azure_blob_prefix)
        return f"{prefix}/{super()._full_key(key)}"

    def _container_client(self):
        if self._client is not None:
            return self._client
        account = validate_cloud_storage_ref(
            os.getenv(self.settings.azure_storage_account_ref, ""),
            self.name,
        )
        credential_type = import_module("azure.identity").DefaultAzureCredential
        service_type = import_module("azure.storage.blob").BlobServiceClient
        service = service_type(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=credential_type(),
        )
        return service.get_container_client(self._container())

    def _blob(self, key: str):
        return self._container_client().get_blob_client(key)

    def _write(self, key: str, data: bytes) -> None:
        self._blob(key).upload_blob(
            data,
            overwrite=self.settings.storage_provider_cloud_allow_overwrite,
        )

    def _read(self, key: str) -> bytes:
        return self._blob(key).download_blob().readall()

    def _exists(self, key: str) -> bool:
        try:
            self._blob(key).get_blob_properties()
        except Exception as exc:
            if _is_not_found_exception(exc):
                return False
            raise
        return True

    def _delete(self, key: str) -> None:
        self._blob(key).delete_blob()

    def _list(self) -> list[tuple[str, int | None]]:
        return [
            (str(item.name), getattr(item, "size", None))
            for item in self._container_client().list_blobs(
                name_starts_with=f"{self.settings.azure_blob_prefix}/"
            )
        ]


class GcsStorageProvider(OptionalCloudStorageProvider):
    name = "gcs"
    dependency = "google.cloud.storage"
    enabled_setting = "gcs_storage_enabled"

    def _config_ready(self) -> bool:
        return bool(
            self.settings.gcs_project_id_ref
            and os.getenv(self.settings.gcs_project_id_ref, "").strip()
            and self.settings.gcs_bucket_ref
            and os.getenv(self.settings.gcs_bucket_ref, "").strip()
        )

    def _bucket_name(self) -> str:
        return validate_cloud_storage_ref(
            os.getenv(self.settings.gcs_bucket_ref, ""),
            self.name,
            allow_gcs_resource=(
                self.settings.gcs_allow_resource_names
                or self.settings.gcs_allow_gs_urls
            ),
        )

    def _full_key(self, key: str) -> str:
        prefix = validate_storage_key(self.settings.gcs_key_prefix)
        return f"{prefix}/{super()._full_key(key)}"

    def _storage_client(self):
        if self._client is not None:
            return self._client
        client_type = import_module("google.cloud.storage").Client
        return client_type(project=os.getenv(self.settings.gcs_project_id_ref, ""))

    def _blob(self, key: str):
        return self._storage_client().bucket(self._bucket_name()).blob(key)

    def _write(self, key: str, data: bytes) -> None:
        kwargs = (
            {}
            if self.settings.storage_provider_cloud_allow_overwrite
            else {"if_generation_match": 0}
        )
        self._blob(key).upload_from_string(data, **kwargs)

    def _read(self, key: str) -> bytes:
        return self._blob(key).download_as_bytes()

    def _exists(self, key: str) -> bool:
        try:
            return bool(self._blob(key).exists())
        except Exception as exc:
            if _is_not_found_exception(exc):
                return False
            raise

    def _delete(self, key: str) -> None:
        self._blob(key).delete()

    def _list(self) -> list[tuple[str, int | None]]:
        return [
            (str(item.name), getattr(item, "size", None))
            for item in self._storage_client().list_blobs(
                self._bucket_name(),
                prefix=f"{self.settings.gcs_key_prefix}/",
            )
        ]


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


_CLOUD_STORAGE_PROVIDERS = {
    CloudStorageProviderKind.S3: S3StorageProvider,
    CloudStorageProviderKind.AZURE_BLOB: AzureBlobStorageProvider,
    CloudStorageProviderKind.GCS: GcsStorageProvider,
}


def build_cloud_storage_provider_health(
    kind: CloudStorageProviderKind | str,
    settings: Settings,
) -> CloudStorageProviderHealth:
    provider_kind = CloudStorageProviderKind(kind)
    provider = _CLOUD_STORAGE_PROVIDERS[provider_kind](settings)
    enabled = provider._enabled()
    dependency_available = provider._dependency_present()
    configured = provider._config_ready()
    confirmation_present = provider._confirmation_present()
    operations_allowed = bool(
        enabled
        and dependency_available
        and configured
        and settings.storage_provider_cloud_network_enabled
        and confirmation_present
    )
    findings: list[CloudStorageProviderFinding] = []
    next_steps: list[str] = []
    if not enabled:
        status = CloudStorageProviderStatus.DISABLED
        findings.append(
            CloudStorageProviderFinding(
                code="provider_disabled",
                severity="info",
                message="Cloud storage provider is disabled by default.",
            )
        )
        next_steps.append("Keep local storage unless an operator selects this provider.")
    elif not dependency_available:
        status = CloudStorageProviderStatus.DEPENDENCY_MISSING
        findings.append(
            CloudStorageProviderFinding(
                code="dependency_missing",
                severity="warning",
                message="Optional cloud storage dependency is not installed.",
            )
        )
        next_steps.append("Install the matching optional extra in the private runtime.")
    elif not configured:
        status = CloudStorageProviderStatus.NEEDS_CONFIGURATION
        findings.append(
            CloudStorageProviderFinding(
                code="needs_configuration",
                severity="warning",
                message="Required private configuration references are unresolved.",
            )
        )
        next_steps.append("Configure private references without printing their values.")
    elif not operations_allowed:
        status = CloudStorageProviderStatus.BLOCKED
        findings.append(
            CloudStorageProviderFinding(
                code="operations_gated",
                severity="info",
                message="Operations remain blocked by network and confirmation gates.",
            )
        )
        next_steps.append("Keep cloud network disabled until a deliberate private operation.")
    else:
        status = CloudStorageProviderStatus.READY_FOR_OPERATIONS
        findings.append(
            CloudStorageProviderFinding(
                code="operations_ready",
                severity="info",
                message="Gates permit operations; no operation was attempted.",
            )
        )
    return CloudStorageProviderHealth(
        provider=provider_kind,
        status=status,
        enabled=enabled,
        dependency_available=dependency_available,
        dependency_missing=not dependency_available,
        cloud_network_enabled=settings.storage_provider_cloud_network_enabled,
        cloud_confirmation_present=confirmation_present,
        configured=configured,
        operations_allowed=operations_allowed,
        findings=findings,
        recommended_next_steps=next_steps,
    )


def build_all_cloud_storage_provider_health(
    settings: Settings,
) -> list[CloudStorageProviderHealth]:
    return [
        build_cloud_storage_provider_health(kind, settings)
        for kind in CloudStorageProviderKind
    ]


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
    "build_all_cloud_storage_provider_health",
    "build_cloud_storage_provider_health",
    "build_storage_provider",
    "build_storage_provider_health",
    "build_storage_provider_readiness",
    "collect_required_storage_refs",
    "mask_storage_ref",
    "normalize_storage_key",
    "validate_required_storage_refs",
    "validate_cloud_storage_ref",
    "validate_storage_key",
    "CLOUD_STORAGE_CONFIRMATION_PHRASE",
]
