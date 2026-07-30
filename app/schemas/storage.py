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


class CloudStorageProviderKind(StrEnum):
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"


class CloudStorageProviderStatus(StrEnum):
    DISABLED = "disabled"
    DEPENDENCY_MISSING = "dependency_missing"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"
    READY_FOR_OPERATIONS = "ready_for_operations"


class CloudStorageProviderDependencyStatus(StrEnum):
    AVAILABLE = "available"
    DEPENDENCY_MISSING = "dependency_missing"


class CloudStorageProviderConfigStatus(StrEnum):
    CONFIGURED = "configured"
    NEEDS_CONFIGURATION = "needs_configuration"


class CloudStorageProviderFinding(StrictStorageModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class CloudStorageOperationPolicy(StrictStorageModel):
    provider: CloudStorageProviderKind
    enabled: bool
    cloud_provider_allowed: bool
    cloud_network_enabled: bool
    cloud_confirmation_present: bool
    configured: bool
    operations_allowed: bool
    list_allowed: bool = False
    delete_allowed: bool = False
    overwrite_allowed: bool = False
    presigned_urls_allowed: bool = False
    fail_closed: bool = True


class CloudStorageProviderHealth(StrictStorageModel):
    provider: CloudStorageProviderKind
    status: CloudStorageProviderStatus
    enabled: bool
    dependency_available: bool
    dependency_missing: bool
    cloud_network_enabled: bool
    cloud_confirmation_present: bool
    configured: bool
    operations_allowed: bool
    health_network_check_attempted: bool = False
    contents_exposed: bool = False
    bucket_names_exposed: bool = False
    object_keys_exposed: bool = False
    credentials_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    external_calls: bool = False
    findings: list[CloudStorageProviderFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


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
