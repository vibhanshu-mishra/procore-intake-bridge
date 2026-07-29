from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictFlowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlowMode(StrEnum):
    DEMO = "demo"
    SANDBOX = "sandbox"
    PILOT = "pilot"


class FlowStage(StrEnum):
    DEMO = "demo"
    SANDBOX_PREFLIGHT = "sandbox_preflight"
    SANDBOX_ONBOARDING = "sandbox_onboarding"
    SANDBOX_SMOKE = "sandbox_smoke"
    SANDBOX_VALIDATION = "sandbox_validation"
    PILOT_PREFLIGHT = "pilot_preflight"
    PILOT_APPROVAL = "pilot_approval"
    PILOT_LAUNCH_HOLD = "pilot_launch_hold"


class FlowStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class FlowDecision(StrEnum):
    DEMO_READY = "demo_ready"
    SANDBOX_READY = "sandbox_ready"
    SANDBOX_NEEDS_CONFIGURATION = "sandbox_needs_configuration"
    PILOT_READY_FOR_PRIVATE_REVIEW = "pilot_ready_for_private_review"
    PILOT_NEEDS_CONFIGURATION = "pilot_needs_configuration"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class FlowFinding(StrictFlowModel):
    code: str
    severity: str
    message: str


class FlowRequirement(StrictFlowModel):
    requirement: str
    stage: FlowStage
    status: FlowStatus
    message: str


class FlowMilestone(StrictFlowModel):
    stage: FlowStage
    status: FlowStatus
    message: str


class FlowEvidenceRef(StrictFlowModel):
    kind: str
    reference: str
    status: FlowStatus = FlowStatus.NEEDS_REVIEW


class FlowProfile(StrictFlowModel):
    profile_name: str
    selected_path: FlowMode
    environment_label: str = "EXAMPLE_ENVIRONMENT_PLACEHOLDER"
    demo_status: FlowStatus = FlowStatus.READY
    private_workspace_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    dmsa_refs_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    admin_auth_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    allowed_scope_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    permission_review_status: FlowStatus = FlowStatus.NEEDS_REVIEW
    sandbox_smoke_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    sandbox_smoke_ref: str = "SANDBOX_SMOKE_REF_PLACEHOLDER"
    webhook_review_status: FlowStatus = FlowStatus.NEEDS_REVIEW
    secret_provider_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    storage_provider_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    database_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    deployment_recipe_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    support_diagnostics_status: FlowStatus = FlowStatus.NEEDS_REVIEW
    evidence_manifest_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    evidence_review_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    pilot_readiness_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    pilot_approval_status: FlowStatus = FlowStatus.NEEDS_REVIEW
    rollback_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    backup_status: FlowStatus = FlowStatus.NEEDS_CONFIGURATION
    incident_response_status: FlowStatus = FlowStatus.NEEDS_REVIEW
    legal_privacy_review_placeholder: str = "LEGAL_PRIVACY_REVIEW_PLACEHOLDER"
    customer_approval_placeholder: str = "CUSTOMER_APPROVAL_PLACEHOLDER"
    internal_operator_approval_placeholder: str = "OPERATOR_APPROVAL_PLACEHOLDER"
    known_limitations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FlowReadinessReport(StrictFlowModel):
    profile_name: str
    selected_path: FlowMode
    decision: FlowDecision
    status: FlowStatus
    requirements: list[FlowRequirement]
    milestones: list[FlowMilestone]
    findings: list[FlowFinding]
    next_steps: list[str]
    external_calls: bool = False
    pilot_approved: bool = False
    deployment_executed: bool = False
    private_evidence_read: bool = False
    values_exposed: bool = False


class FlowArtifactResult(StrictFlowModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    values_exposed: bool = False
    local_paths_exposed: bool = False


class FlowTransitionSummary(StrictFlowModel):
    selected_path: FlowMode
    decision: FlowDecision
    current_stage: FlowStage
    next_stage: FlowStage
    next_steps: list[str]
    pilot_approved: bool = False
