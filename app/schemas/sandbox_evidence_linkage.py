from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictSandboxEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SandboxEvidenceType(StrEnum):
    SANDBOX_SMOKE = "sandbox_smoke"
    SANDBOX_READ_VALIDATION = "sandbox_read_validation"
    SANDBOX_PERMISSIONS_REVIEW = "sandbox_permissions_review"
    SANDBOX_WEBHOOK_REVIEW = "sandbox_webhook_review"
    SANDBOX_SCOPE_REVIEW = "sandbox_scope_review"
    SANDBOX_OPERATOR_REVIEW = "sandbox_operator_review"


class SandboxEvidenceStatus(StrEnum):
    ACCEPTED_PLACEHOLDER = "accepted_placeholder"
    NEEDS_REVIEW = "needs_review"
    MISSING = "missing"
    EXPIRED_PLACEHOLDER = "expired_placeholder"
    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"


class SandboxEvidenceFinding(StrictSandboxEvidenceModel):
    code: str
    status: SandboxEvidenceStatus
    message: str
    blocking: bool = False


class SandboxEvidenceRef(StrictSandboxEvidenceModel):
    evidence_type: SandboxEvidenceType
    evidence_ref: str
    status: SandboxEvidenceStatus = SandboxEvidenceStatus.ACCEPTED_PLACEHOLDER
    review_required: bool = True
    report_contents_included: bool = False


class SandboxEvidenceLinkageProfile(StrictSandboxEvidenceModel):
    profile_name: str
    evidence_refs: list[SandboxEvidenceRef] = Field(default_factory=list)
    sandbox_smoke_ref: str = "SANDBOX_SMOKE_REF_PLACEHOLDER"
    sandbox_read_validation_ref: str = "SANDBOX_READ_VALIDATION_REF_PLACEHOLDER"
    permission_review_ref: str = "SANDBOX_PERMISSION_REVIEW_REF_PLACEHOLDER"
    webhook_review_ref: str = "SANDBOX_WEBHOOK_REVIEW_REF_PLACEHOLDER"
    scope_review_ref: str = "SANDBOX_SCOPE_REVIEW_REF_PLACEHOLDER"
    operator_review_ref: str = "SANDBOX_OPERATOR_REVIEW_REF_PLACEHOLDER"
    reviewer_placeholder: str = "SANDBOX_EVIDENCE_REVIEWER_PLACEHOLDER"
    expiry_placeholder: str = "SANDBOX_EVIDENCE_EXPIRY_PLACEHOLDER"
    renewal_placeholder: str = "SANDBOX_EVIDENCE_RENEWAL_PLACEHOLDER"
    known_limitations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SandboxEvidencePilotMapping(StrictSandboxEvidenceModel):
    workflow: str
    reference_placeholders: list[str]
    mapping_placeholder: str
    human_review_required: bool = True
    approval_granted: bool = False
    report_contents_included: bool = False


class SandboxEvidenceLinkageReport(StrictSandboxEvidenceModel):
    generated_at: datetime
    profile_name: str
    status: SandboxEvidenceStatus
    refs_total: int
    required_refs_present: bool
    pilot_readiness_mapping: SandboxEvidencePilotMapping
    approval_packet_mapping: SandboxEvidencePilotMapping
    flow_mapping: SandboxEvidencePilotMapping
    evidence_review_mapping: SandboxEvidencePilotMapping
    findings: list[SandboxEvidenceFinding]
    recommended_next_steps: list[str]
    secrets_exposed: bool = False
    ids_exposed: bool = False
    private_paths_exposed: bool = False
    report_contents_exposed: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    private_evidence_read: bool = False
    pilot_approved: bool = False


class SandboxEvidenceArtifactResult(StrictSandboxEvidenceModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    procore_calls: bool = False
    report_contents_included: bool = False
    private_paths_included: bool = False
    pilot_approved: bool = False
