from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictSecretModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SecretProviderKind(StrEnum):
    DISABLED = "disabled"
    ENV = "env"
    FILE = "file"
    TEST = "test"
    EXTERNAL_PLACEHOLDER = "external_placeholder"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"


class SecretRef(StrictSecretModel):
    masked_ref: str
    provider: SecretProviderKind


class SecretRefStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    UNKNOWN = "unknown"
    RESOLUTION_NOT_ATTEMPTED = "resolution_not_attempted"


class SecretProviderFinding(StrictSecretModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class SecretProviderInventoryItem(StrictSecretModel):
    purpose: str
    masked_ref: str
    status: SecretRefStatus


class SecretProviderHealth(StrictSecretModel):
    provider: SecretProviderKind
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
    resolution_not_attempted: bool = True
    checked_refs_count: int = 0
    present_refs_count: int = 0
    missing_refs_count: int = 0
    refs: list[SecretProviderInventoryItem] = []
    values_exposed: bool = False
    external_calls: bool = False


class SecretProviderReadiness(StrictSecretModel):
    provider: SecretProviderKind
    ready: bool
    health: SecretProviderHealth
    findings: list[SecretProviderFinding]
    values_exposed: bool = False
    external_calls: bool = False


class SecretProviderResolutionResult(StrictSecretModel):
    provider: SecretProviderKind
    masked_ref: str
    resolved: bool
    value_exposed: bool = False
