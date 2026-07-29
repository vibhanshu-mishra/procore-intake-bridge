from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.private_evidence import EvidenceItemType, EvidenceSensitivityLevel


class StrictReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReviewEnvironment(StrEnum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class EvidenceReviewStatus(StrEnum):
    NOT_STARTED = "not_started"
    NEEDS_REVIEW = "needs_review"
    REVIEWED_PLACEHOLDER = "reviewed_placeholder"
    ACCEPTED_PLACEHOLDER = "accepted_placeholder"
    REJECTED_PLACEHOLDER = "rejected_placeholder"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class EvidenceExpiryStatus(StrEnum):
    CURRENT = "current"
    NEEDS_REVIEW = "needs_review"
    EXPIRES_SOON = "expires_soon"
    EXPIRED = "expired"
    RENEWAL_REQUIRED = "renewal_required"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class EvidenceReviewDecision(StrEnum):
    PENDING = "pending"
    ACCEPT_PLACEHOLDER = "accept_placeholder"
    REJECT_PLACEHOLDER = "reject_placeholder"
    RENEWAL_REQUIRED = "renewal_required"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class EvidenceReviewerPlaceholder(StrictReviewModel):
    reviewer_placeholder: str = "REVIEWER_PLACEHOLDER"
    approver_placeholder: str = "APPROVER_PLACEHOLDER"
    signoff_placeholder: str = "SIGNOFF_PLACEHOLDER"


class EvidenceReviewItem(StrictReviewModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    evidence_type: EvidenceItemType
    related_gate: str = ""
    evidence_ref_placeholder: str = Field(min_length=1, max_length=240)
    review_status: EvidenceReviewStatus = EvidenceReviewStatus.NOT_STARTED
    expiry_status: EvidenceExpiryStatus = EvidenceExpiryStatus.NEEDS_REVIEW
    reviewer_placeholder: EvidenceReviewerPlaceholder = Field(
        default_factory=EvidenceReviewerPlaceholder
    )
    reviewed_at_placeholder: str = "REVIEWED_AT_PLACEHOLDER"
    expires_at_placeholder: str = "EXPIRES_AT_PLACEHOLDER"
    renewal_required: bool = False
    renewal_reason: str = ""
    decision: EvidenceReviewDecision = EvidenceReviewDecision.PENDING
    notes: list[str] = Field(default_factory=list)
    sensitivity: EvidenceSensitivityLevel = EvidenceSensitivityLevel.PLACEHOLDER
    redaction_required: bool = True
    required_for_gate: bool = True


class EvidenceReviewProfile(StrictReviewModel):
    schema_version: str = "1.0"
    profile_name: str = Field(min_length=1, max_length=100)
    review_label: str = Field(min_length=1, max_length=200)
    customer_label: str = "Example Customer"
    environment: EvidenceReviewEnvironment = EvidenceReviewEnvironment.STAGING
    review_owner_placeholder: str = "REVIEW_OWNER_PLACEHOLDER"
    review_cycle_placeholder: str = "REVIEW_CYCLE_PLACEHOLDER"
    source_evidence_manifest_ref: str = "EVIDENCE_MANIFEST_REF_PLACEHOLDER"


class EvidenceReviewManifest(EvidenceReviewProfile):
    review_items: list[EvidenceReviewItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvidenceReviewFinding(StrictReviewModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str
    evidence_id: str = ""


class EvidenceReviewGateResult(StrictReviewModel):
    evidence_id: str
    evidence_type: str
    review_status: EvidenceReviewStatus
    expiry_status: EvidenceExpiryStatus
    renewal_required: bool
    blocks_gate: bool


class EvidenceReviewSummary(StrictReviewModel):
    total_items: int
    current_items: int
    needs_review_items: int
    expires_soon_items: int
    expired_items: int
    renewal_required_items: int
    blocked_items: int


class EvidenceReviewReport(StrictReviewModel):
    generated_at: datetime
    profile_name: str
    environment: str
    valid: bool
    blocking_findings_count: int
    warning_findings_count: int
    findings: list[EvidenceReviewFinding]
    gates: list[EvidenceReviewGateResult]
    summary: EvidenceReviewSummary
    local_only: bool = True
    external_calls: bool = False
    procore_calls: bool = False
    notifications_sent: bool = False
    file_contents_read: bool = False
    values_exposed: bool = False


class EvidenceRenewalChecklistSection(StrictReviewModel):
    title: str
    items: list[str]


class EvidenceReviewArtifactResult(StrictReviewModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    notifications_sent: bool = False
    file_contents_included: bool = False
    values_exposed: bool = False
