from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.config import Settings
from app.services.attachment_storage_keys import (
    calculate_attachment_integrity_metadata,
    mask_storage_key,
    validate_storage_key,
)


class AttachmentStorageProviderError(RuntimeError):
    """Storage operation failed without leaking private configuration."""


class AttachmentStorageUnavailableError(AttachmentStorageProviderError):
    pass


class AttachmentStorageMisconfiguredError(AttachmentStorageProviderError):
    pass


class AttachmentStorageBlockedError(AttachmentStorageProviderError):
    pass


class AttachmentStorageObjectNotFoundError(AttachmentStorageProviderError):
    pass


class AttachmentStorageHealth(BaseModel):
    provider: str
    status: str
    available: bool
    implemented: bool = True
    checked_keys: int = 0
    missing_keys: int = 0
    message: str


class AttachmentStorageWriteResult(BaseModel):
    provider: str
    storage_key: str
    size_bytes: int
    checksum_sha256: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttachmentStorageReadResult(AttachmentStorageWriteResult):
    data: bytes = Field(exclude=True)


class AttachmentStorageProvider(Protocol):
    name: str

    def write_bytes(
        self, key: str, data: bytes, metadata: dict | None = None, overwrite: bool = False
    ) -> AttachmentStorageWriteResult: ...
    def read_bytes(self, key: str) -> AttachmentStorageReadResult: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def list_objects(self) -> list[dict]: ...
    def describe_object(self, key: str) -> dict: ...
    def health_check(self, required_keys: list[str] | None = None) -> AttachmentStorageHealth: ...
    def summarize_config(self) -> dict: ...


class LocalAttachmentStorageProvider:
    name = "local"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.attachment_storage_root.resolve()

    def _target(self, key: str) -> tuple[str, Path]:
        safe_key = validate_storage_key(key, self.settings)
        target = (self.root / safe_key).resolve()
        if not target.is_relative_to(self.root):
            raise AttachmentStorageBlockedError(
                "Attachment storage key escaped its configured root."
            )
        return safe_key, target

    def write_bytes(
        self, key: str, data: bytes, metadata: dict | None = None, overwrite: bool = False
    ) -> AttachmentStorageWriteResult:
        safe_key, target = self._target(key)
        if len(data) > self.settings.attachment_storage_max_object_bytes:
            raise AttachmentStorageBlockedError(
                "Attachment exceeds the configured object-size limit."
            )
        if self.settings.attachment_storage_write_metadata_only:
            raise AttachmentStorageBlockedError(
                "Attachment byte writes are disabled by metadata-only mode."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not (overwrite and self.settings.attachment_allow_overwrite):
            raise AttachmentStorageBlockedError("Attachment exists and overwrite is disabled.")
        target.write_bytes(data)
        integrity = calculate_attachment_integrity_metadata(data)
        return AttachmentStorageWriteResult(
            provider=self.name, storage_key=safe_key, metadata=dict(metadata or {}), **integrity
        )

    def read_bytes(self, key: str) -> AttachmentStorageReadResult:
        safe_key, target = self._target(key)
        if not target.is_file():
            raise AttachmentStorageObjectNotFoundError("Attachment object was not found.")
        data = target.read_bytes()
        return AttachmentStorageReadResult(
            provider=self.name,
            storage_key=safe_key,
            data=data,
            **calculate_attachment_integrity_metadata(data),
        )

    def exists(self, key: str) -> bool:
        _, target = self._target(key)
        return target.is_file()

    def delete(self, key: str) -> bool:
        _, target = self._target(key)
        if not target.is_file():
            return False
        target.unlink()
        return True

    def list_objects(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        items = []
        for target in self.root.rglob("*"):
            if not target.is_file():
                continue
            resolved = target.resolve()
            if not resolved.is_relative_to(self.root):
                raise AttachmentStorageBlockedError(
                    "Attachment storage object escaped its configured root."
                )
            key = target.relative_to(self.root).as_posix()
            items.append(self.describe_object(key))
        return items

    def describe_object(self, key: str) -> dict:
        safe_key, target = self._target(key)
        return {
            "provider": self.name,
            "storage_key": mask_storage_key(safe_key),
            "exists": target.is_file(),
            "size_bytes": target.stat().st_size if target.is_file() else None,
        }

    def health_check(self, required_keys: list[str] | None = None) -> AttachmentStorageHealth:
        keys = required_keys or []
        missing = sum(not self.exists(key) for key in keys)
        return AttachmentStorageHealth(
            provider=self.name,
            status="healthy" if not missing else "degraded",
            available=True,
            checked_keys=len(keys),
            missing_keys=missing,
            message="Local storage provider is available.",
        )

    def summarize_config(self) -> dict:
        return {
            "provider": self.name,
            "root_configured": bool(str(self.settings.attachment_storage_root)),
            "root_is_absolute": self.settings.attachment_storage_root.is_absolute(),
            "external_calls": False,
        }


class TestAttachmentStorageProvider:
    name = "test"

    def __init__(self, settings: Settings, storage: dict[str, bytes] | None = None):
        self.settings = settings
        self.storage = storage if storage is not None else {}

    def write_bytes(
        self, key: str, data: bytes, metadata: dict | None = None, overwrite: bool = False
    ) -> AttachmentStorageWriteResult:
        safe_key = validate_storage_key(key, self.settings)
        if len(data) > self.settings.attachment_storage_max_object_bytes:
            raise AttachmentStorageBlockedError(
                "Attachment exceeds the configured object-size limit."
            )
        if safe_key in self.storage and not overwrite:
            raise AttachmentStorageBlockedError("Attachment exists and overwrite is disabled.")
        self.storage[safe_key] = bytes(data)
        return AttachmentStorageWriteResult(
            provider=self.name,
            storage_key=safe_key,
            metadata=dict(metadata or {}),
            **calculate_attachment_integrity_metadata(data),
        )

    def read_bytes(self, key: str) -> AttachmentStorageReadResult:
        safe_key = validate_storage_key(key, self.settings)
        if safe_key not in self.storage:
            raise AttachmentStorageObjectNotFoundError("Attachment object was not found.")
        data = self.storage[safe_key]
        return AttachmentStorageReadResult(
            provider=self.name,
            storage_key=safe_key,
            data=data,
            **calculate_attachment_integrity_metadata(data),
        )

    def exists(self, key: str) -> bool:
        return validate_storage_key(key, self.settings) in self.storage

    def delete(self, key: str) -> bool:
        safe_key = validate_storage_key(key, self.settings)
        return self.storage.pop(safe_key, None) is not None

    def list_objects(self) -> list[dict]:
        return [self.describe_object(key) for key in sorted(self.storage)]

    def describe_object(self, key: str) -> dict:
        safe_key = validate_storage_key(key, self.settings)
        return {
            "provider": self.name,
            "storage_key": mask_storage_key(safe_key),
            "exists": safe_key in self.storage,
            "size_bytes": len(self.storage[safe_key]) if safe_key in self.storage else None,
        }

    def health_check(self, required_keys: list[str] | None = None) -> AttachmentStorageHealth:
        keys = required_keys or []
        missing = sum(not self.exists(key) for key in keys)
        return AttachmentStorageHealth(
            provider=self.name,
            status="healthy" if not missing else "degraded",
            available=True,
            checked_keys=len(keys),
            missing_keys=missing,
            message="In-memory test storage is available.",
        )

    def summarize_config(self) -> dict:
        return {"provider": self.name, "in_memory": True, "external_calls": False}


class DisabledAttachmentStorageProvider:
    name = "disabled"

    def _blocked(self):
        raise AttachmentStorageBlockedError("Attachment storage is disabled.")

    def write_bytes(self, key, data, metadata=None, overwrite=False):
        self._blocked()

    def read_bytes(self, key):
        self._blocked()

    def exists(self, key):
        self._blocked()

    def describe_object(self, key):
        self._blocked()

    def delete(self, key):
        self._blocked()

    def list_objects(self):
        self._blocked()

    def health_check(self, required_keys=None):
        return AttachmentStorageHealth(
            provider=self.name,
            status="disabled",
            available=False,
            message="Attachment storage is disabled.",
        )

    def summarize_config(self):
        return {"provider": self.name, "external_calls": False}


class ExternalPlaceholderAttachmentStorageProvider(DisabledAttachmentStorageProvider):
    name = "external_placeholder"

    def _blocked(self):
        raise AttachmentStorageUnavailableError("External attachment storage is not implemented.")

    def health_check(self, required_keys=None):
        return AttachmentStorageHealth(
            provider=self.name,
            status="not_implemented",
            available=False,
            implemented=False,
            message="External attachment storage adapter is not implemented.",
        )

    def summarize_config(self):
        return {
            "provider": self.name,
            "provider_name_configured": False,
            "bucket_reference_configured": False,
            "endpoint_reference_configured": False,
            "region_configured": False,
            "external_calls": False,
        }
