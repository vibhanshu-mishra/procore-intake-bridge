from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictApprovalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PilotApprovalEnvironment(StrEnum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class PilotApprovalDecision(StrEnum):
    DRAFT_PLACEHOLDER = "draft_placeholder"
    READY_FOR_PRIVATE_REVIEW = "ready_for_private_review"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    APPROVED_PLACEHOLDER = "approved_placeholder"
    REJECTED_PLACEHOLDER = "rejected_placeholder"
    NOT_APPLICABLE = "not_applicable"


class PilotApprovalStatus(StrEnum):
    DRAFT_PLACEHOLDER = "draft_placeholder"
    READY_FOR_PRIVATE_REVIEW = "ready_for_private_review"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    APPROVED_PLACEHOLDER = "approved_placeholder"
    REJECTED_PLACEHOLDER = "rejected_placeholder"
    NOT_APPLICABLE = "not_applicable"


class PilotApprovalEvidenceSummary(StrictApprovalModel):
    evidence_manifest_ref: str = "PRIVATE_EVIDENCE_REF_PLACEHOLDER"
    evidence_item_count_placeholder: str = "EVIDENCE_ITEM_COUNT_PLACEHOLDER"
    evidence_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW


class PilotApprovalReadinessSummary(StrictApprovalModel):
    pilot_readiness_decision_ref: str = "PILOT_READINESS_REF_PLACEHOLDER"
    pilot_readiness_decision_status: str = "NEEDS_REVIEW"


class PilotApprovalReviewSummary(StrictApprovalModel):
    evidence_review_ref: str = "EVIDENCE_REVIEW_REF_PLACEHOLDER"
    evidence_review_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    expired_evidence_count: int = Field(default=0, ge=0)
    renewal_required_count: int = Field(default=0, ge=0)


class PilotApprovalLaunchCondition(StrictApprovalModel):
    condition_id: str
    description_placeholder: str
    required: bool = True
    status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    evidence_ref_placeholder: str = "CONDITION_EVIDENCE_REF_PLACEHOLDER"


class PilotApprovalRollbackCondition(StrictApprovalModel):
    condition_id: str
    trigger_placeholder: str
    response_placeholder: str
    status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    evidence_ref_placeholder: str = "ROLLBACK_EVIDENCE_REF_PLACEHOLDER"


class PilotApprovalKnownLimitation(StrictApprovalModel):
    limitation_id: str
    description_placeholder: str
    impact_placeholder: str
    mitigation_placeholder: str
    status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW


class PilotApprovalRiskAcceptance(StrictApprovalModel):
    limitation_ref: str
    acceptance_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    owner_placeholder: str = "RISK_OWNER_PLACEHOLDER"
    rationale_placeholder: str = "RISK_RATIONALE_PLACEHOLDER"
    review_ref_placeholder: str = "RISK_REVIEW_REF_PLACEHOLDER"


class PilotApprovalSignoffPlaceholder(StrictApprovalModel):
    role_placeholder: str
    reviewer_placeholder: str = "REVIEWER_PLACEHOLDER"
    approver_placeholder: str = "APPROVER_PLACEHOLDER"
    decision: PilotApprovalDecision = PilotApprovalDecision.DRAFT_PLACEHOLDER
    reviewed_at_placeholder: str = "REVIEWED_AT_PLACEHOLDER"
    signoff_ref_placeholder: str = "SIGNOFF_REF_PLACEHOLDER"


class PilotApprovalPacket(StrictApprovalModel):
    schema_version: str = "1.0"
    packet_name: str = Field(min_length=1, max_length=100)
    pilot_label: str = Field(min_length=1, max_length=200)
    customer_label: str = "Example Customer"
    environment: PilotApprovalEnvironment = PilotApprovalEnvironment.STAGING
    readiness: PilotApprovalReadinessSummary
    evidence: PilotApprovalEvidenceSummary
    review: PilotApprovalReviewSummary
    support_diagnostics_ref: str = "SUPPORT_DIAGNOSTICS_REF_PLACEHOLDER"
    support_redaction_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    sandbox_smoke_ref: str = "SANDBOX_SMOKE_REF_PLACEHOLDER"
    sandbox_smoke_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    webhook_verification_ref: str = "WEBHOOK_VERIFICATION_REF_PLACEHOLDER"
    webhook_verification_status: PilotApprovalStatus = PilotApprovalStatus.NOT_APPLICABLE
    migration_safety_ref: str = "MIGRATION_SAFETY_REF_PLACEHOLDER"
    migration_safety_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    customer_deployment_profile_ref: str = "CUSTOMER_DEPLOYMENT_REF_PLACEHOLDER"
    customer_deployment_status: PilotApprovalStatus = PilotApprovalStatus.NEEDS_REVIEW
    launch_conditions: list[PilotApprovalLaunchCondition] = Field(default_factory=list)
    rollback_conditions: list[PilotApprovalRollbackCondition] = Field(default_factory=list)
    known_limitations: list[PilotApprovalKnownLimitation] = Field(default_factory=list)
    risk_acceptance: list[PilotApprovalRiskAcceptance] = Field(default_factory=list)
    signoff_placeholders: list[PilotApprovalSignoffPlaceholder] = Field(
        default_factory=list
    )
    approval_decision: PilotApprovalDecision = PilotApprovalDecision.DRAFT_PLACEHOLDER
    approval_status: PilotApprovalStatus = PilotApprovalStatus.DRAFT_PLACEHOLDER
    approval_notes: list[str] = Field(default_factory=list)
    generated_by_placeholder: str = "PACKET_GENERATOR_PLACEHOLDER"
    reviewed_by_placeholders: list[str] = Field(default_factory=list)
    approved_by_placeholders: list[str] = Field(default_factory=list)


class PilotApprovalFinding(StrictApprovalModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class PilotApprovalGateResult(StrictApprovalModel):
    gate: str
    passed: bool
    status: PilotApprovalStatus
    summary: str


class PilotApprovalPacketSummary(StrictApprovalModel):
    launch_conditions: int
    rollback_conditions: int
    known_limitations: int
    risk_acceptances: int
    signoff_placeholders: int
    expired_evidence_count: int
    renewal_required_count: int


class PilotApprovalValidationReport(StrictApprovalModel):
    generated_at: datetime
    packet_name: str
    environment: str
    evaluation: PilotApprovalStatus
    blocking_findings_count: int
    review_findings_count: int
    findings: list[PilotApprovalFinding]
    gates: list[PilotApprovalGateResult]
    summary: PilotApprovalPacketSummary
    local_only: bool = True
    external_calls: bool = False
    procore_calls: bool = False
    notifications_sent: bool = False
    approved_real_pilot: bool = False
    file_contents_read: bool = False
    values_exposed: bool = False


class PilotApprovalArtifactResult(StrictApprovalModel):
    packet_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    notifications_sent: bool = False
    file_contents_included: bool = False
    approved_real_pilot: bool = False
    values_exposed: bool = False
