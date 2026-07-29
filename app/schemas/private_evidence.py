from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceWorkspaceEnvironment(StrEnum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class EvidenceItemType(StrEnum):
    DMSA_ONBOARDING = "dmsa_onboarding"
    GC_OWNER_PERMISSIONS = "gc_owner_permissions"
    PRIVATE_APP_INSTALLATION = "private_app_installation"
    SANDBOX_SMOKE = "sandbox_smoke"
    WEBHOOK_DOCS_VERIFICATION = "webhook_docs_verification"
    WEBHOOK_SIGNATURE_REVIEW = "webhook_signature_review"
    STORAGE_REVIEW = "storage_review"
    MIGRATION_SAFETY = "migration_safety"
    ADMIN_AUTH = "admin_auth"
    SECRET_PROVIDER = "secret_provider"
    SUPPORT_DIAGNOSTICS = "support_diagnostics"
    ROLLBACK_PLAN = "rollback_plan"
    BACKUP_PLAN = "backup_plan"
    INCIDENT_RESPONSE = "incident_response"
    CUSTOMER_APPROVAL = "customer_approval"
    INTERNAL_APPROVAL = "internal_approval"
    DATA_HANDLING_REVIEW = "data_handling_review"
    PROJECT_ALLOWLIST = "project_allowlist"
    KNOWN_LIMITATIONS = "known_limitations"
    PILOT_GO_NO_GO = "pilot_go_no_go"


class EvidenceItemStatus(StrEnum):
    PLANNED = "planned"
    MISSING = "missing"
    COLLECTED = "collected"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"


class EvidenceSensitivityLevel(StrEnum):
    PLACEHOLDER = "placeholder"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class EvidenceReference(StrictEvidenceModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    evidence_ref_placeholder: str = Field(min_length=1, max_length=240)


class EvidenceManifestItem(StrictEvidenceModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    evidence_type: EvidenceItemType
    title: str = Field(min_length=1, max_length=200)
    status: EvidenceItemStatus = EvidenceItemStatus.PLANNED
    sensitivity: EvidenceSensitivityLevel = EvidenceSensitivityLevel.PLACEHOLDER
    owner_placeholder: str = "OWNER_PLACEHOLDER"
    evidence_ref_placeholder: str = "PRIVATE_EVIDENCE_REF_PLACEHOLDER"
    collected_at_placeholder: str = "COLLECTED_AT_PLACEHOLDER"
    expires_at_placeholder: str = "EXPIRES_AT_PLACEHOLDER"
    related_gate: str = ""
    notes: list[str] = Field(default_factory=list)
    redaction_required: bool = True
    file_expected: bool = False
    external_system_placeholder: str = "EXTERNAL_SYSTEM_PLACEHOLDER"


class EvidenceManifest(StrictEvidenceModel):
    schema_version: str = "1.0"
    workspace_name: str = Field(min_length=1, max_length=100)
    workspace_label: str = Field(min_length=1, max_length=200)
    customer_label: str = "Example Customer"
    environment: EvidenceWorkspaceEnvironment = EvidenceWorkspaceEnvironment.STAGING
    purpose: str = "Private pilot evidence metadata planning"
    owner_placeholder: str = "WORKSPACE_OWNER_PLACEHOLDER"
    storage_location_placeholder: str = "PRIVATE_STORAGE_LOCATION_PLACEHOLDER"
    review_cadence_placeholder: str = "REVIEW_CADENCE_PLACEHOLDER"
    evidence_items: list[EvidenceManifestItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvidenceWorkspaceProfile(StrictEvidenceModel):
    manifest: EvidenceManifest
    local_only: bool = True
    external_calls: bool = False
    file_contents_included: bool = False


class EvidenceValidationFinding(StrictEvidenceModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str
    evidence_id: str = ""


class EvidenceValidationReport(StrictEvidenceModel):
    generated_at: datetime
    workspace_name: str
    environment: str
    valid: bool
    blocking_findings_count: int
    warning_findings_count: int
    item_count: int
    findings: list[EvidenceValidationFinding]
    local_only: bool = True
    external_calls: bool = False
    procore_calls: bool = False
    file_contents_read: bool = False
    values_exposed: bool = False


class EvidenceChecklistSection(StrictEvidenceModel):
    title: str
    items: list[str]


class EvidenceArtifactResult(StrictEvidenceModel):
    workspace_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    file_contents_included: bool = False
    values_exposed: bool = False


class EvidenceRedactionReport(StrictEvidenceModel):
    workspace_name: str
    safe_for_local_scaffold: bool
    blocking_findings_count: int
    redaction_required_count: int
    excluded_content_categories: list[str]
    external_calls: bool = False
    values_exposed: bool = False
