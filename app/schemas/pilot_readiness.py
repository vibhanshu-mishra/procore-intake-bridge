from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class PilotReadinessEnvironment(StrEnum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class PilotReadinessEvidenceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class PilotReadinessGateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class PilotReadinessDecision(StrEnum):
    GO = "GO"
    NO_GO = "NO_GO"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


class PilotReadinessEvidenceRef(BaseModel):
    category: str
    status: PilotReadinessEvidenceStatus
    reference: str = ""
    not_applicable_reason: str = ""


class PilotApprovalPlaceholder(BaseModel):
    role: str
    status: PilotReadinessEvidenceStatus = PilotReadinessEvidenceStatus.NEEDS_REVIEW
    approver_placeholder: str = "APPROVER_PLACEHOLDER"
    evidence_ref: str = ""


class PilotReadinessProfile(BaseModel):
    profile_name: str = Field(min_length=1, max_length=100)
    pilot_label: str = Field(min_length=1, max_length=200)
    customer_label: str = "Example Customer"
    environment: PilotReadinessEnvironment = PilotReadinessEnvironment.STAGING
    local_only_dry_run: bool = False
    public_base_url: str = ""
    company_id: str = "COMPANY_ID_PLACEHOLDER"
    project_ids: list[str] = Field(default_factory=list)
    customer_profile_ref: str = ""
    customer_deployment_profile_status: PilotReadinessEvidenceStatus
    dmsa_onboarding_status: PilotReadinessEvidenceStatus
    dmsa_onboarding_ref: str = ""
    gc_owner_permission_status: PilotReadinessEvidenceStatus
    gc_owner_permission_ref: str = ""
    private_app_install_status: PilotReadinessEvidenceStatus
    private_app_install_ref: str = ""
    sandbox_smoke_status: PilotReadinessEvidenceStatus
    sandbox_smoke_report_ref: str = ""
    admin_auth_status: PilotReadinessEvidenceStatus
    admin_auth_mode: Literal["local_optional", "token_required", "disabled"] = "local_optional"
    secret_provider_status: PilotReadinessEvidenceStatus
    secret_provider_kind: Literal[
        "env", "test", "disabled", "external_placeholder", "managed_reference"
    ] = "external_placeholder"
    storage_review_status: PilotReadinessEvidenceStatus
    storage_review_ref: str = ""
    storage_provider_kind: Literal[
        "local", "test", "disabled", "external_placeholder", "managed_reference"
    ] = "external_placeholder"
    database_migration_status: PilotReadinessEvidenceStatus
    migration_safety_status: PilotReadinessEvidenceStatus
    migration_safety_ref: str = ""
    database_profile: str = "sqlite-local"
    webhooks_planned: bool = False
    webhook_docs_status: PilotReadinessEvidenceStatus
    webhook_signature_status: PilotReadinessEvidenceStatus
    webhook_verification_status: PilotReadinessEvidenceStatus
    webhook_verification_ref: str = ""
    support_diagnostics_status: PilotReadinessEvidenceStatus
    support_bundle_redaction_status: PilotReadinessEvidenceStatus
    support_diagnostics_ref: str = ""
    rollback_plan_status: PilotReadinessEvidenceStatus
    rollback_plan_ref: str = ""
    backup_plan_status: PilotReadinessEvidenceStatus
    backup_plan_ref: str = ""
    incident_response_status: PilotReadinessEvidenceStatus
    incident_response_ref: str = ""
    monitoring_plan_status: PilotReadinessEvidenceStatus
    data_handling_review_status: PilotReadinessEvidenceStatus
    data_handling_review_ref: str = ""
    allowed_project_scope_status: PilotReadinessEvidenceStatus
    project_scope_ref: str = ""
    launch_window_placeholder: str = "LAUNCH_WINDOW_PLACEHOLDER"
    pilot_owner_placeholder: str = "PILOT_OWNER_PLACEHOLDER"
    technical_owner_placeholder: str = "TECHNICAL_OWNER_PLACEHOLDER"
    customer_approval_placeholder: PilotApprovalPlaceholder
    internal_approval_placeholder: PilotApprovalPlaceholder
    known_limitations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PilotReadinessGateResult(BaseModel):
    category: str
    status: PilotReadinessGateStatus
    summary: str
    evidence_ref_present: bool = False


class PilotReadinessFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class PilotReadinessReport(BaseModel):
    generated_at: datetime
    profile_name: str
    environment: str
    decision: PilotReadinessDecision
    gates: list[PilotReadinessGateResult]
    findings: list[PilotReadinessFinding]
    blocking_count: int
    review_count: int
    local_planning_only: bool = True
    deployed: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    values_exposed: bool = False


class PilotReadinessArtifactResult(BaseModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    values_exposed: bool = False


class PilotReadinessChecklistSection(BaseModel):
    title: str
    items: list[str]
