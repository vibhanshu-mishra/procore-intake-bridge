from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictStorageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StorageProviderKind(StrEnum):
    DISABLED = "disabled"
    LOCAL = "local"
    TEST = "test"
    EXTERNAL_PLACEHOLDER = "external_placeholder"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"


class StorageObjectStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    UNKNOWN = "unknown"
    OPERATION_NOT_ATTEMPTED = "operation_not_attempted"


class StorageObjectRef(StrictStorageModel):
    provider: StorageProviderKind
    masked_ref: str


class StorageProviderFinding(StrictStorageModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class StorageInventoryItem(StrictStorageModel):
    masked_ref: str
    status: StorageObjectStatus
    size_bytes: int | None = None
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False


class StorageProviderHealth(StrictStorageModel):
    provider: StorageProviderKind
    status: Literal[
        "healthy",
        "degraded",
        "disabled",
        "unavailable",
        "dependency_missing",
        "permission_unknown",
    ]
    configured: bool
    available: bool
    dependency_missing: bool = False
    permission_unknown: bool = False
    operation_not_attempted: bool = True
    items: list[StorageInventoryItem] = Field(default_factory=list)
    value_exposed: bool = False
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False
    external_calls: bool = False


class StorageProviderReadiness(StrictStorageModel):
    provider: StorageProviderKind
    ready: bool
    health: StorageProviderHealth
    findings: list[StorageProviderFinding]
    value_exposed: bool = False
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False
    external_calls: bool = False


class StorageWriteResult(StrictStorageModel):
    provider: StorageProviderKind
    masked_ref: str
    written: bool
    size_bytes: int
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False


class StorageReadResult(StrictStorageModel):
    provider: StorageProviderKind
    masked_ref: str
    found: bool
    size_bytes: int
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False


class StorageDeleteResult(StrictStorageModel):
    provider: StorageProviderKind
    masked_ref: str
    deleted: bool
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False


class StorageListResult(StrictStorageModel):
    provider: StorageProviderKind
    items: list[StorageInventoryItem]
    file_contents_exposed: bool = False
    local_paths_exposed: bool = False
