from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictHostedPilotDryRunModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HostedPilotDryRunStatus(StrEnum):
    READY_FOR_PRIVATE_REHEARSAL = "ready_for_private_rehearsal"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"
    ACCEPTED_PLACEHOLDER = "accepted_placeholder"


class HostedPilotDryRunDecision(StrEnum):
    READY_FOR_PRIVATE_REVIEW = "dry_run_ready_for_private_review"
    NEEDS_REVIEW = "dry_run_needs_review"
    BLOCKED = "dry_run_blocked"
    NOT_RUN = "dry_run_not_run"


class HostedPilotDryRunFinding(StrictHostedPilotDryRunModel):
    code: str
    severity: str = "blocking"
    message: str


class HostedPilotDryRunRequirement(StrictHostedPilotDryRunModel):
    name: str
    required: bool = True
    present: bool
    status: HostedPilotDryRunStatus
    message: str


class HostedPilotDryRunEvidenceRef(StrictHostedPilotDryRunModel):
    name: str
    value: str
    status: HostedPilotDryRunStatus


class HostedPilotDryRunProfile(StrictHostedPilotDryRunModel):
    profile_name: str
    environment_label: str = "ENVIRONMENT_LABEL_PLACEHOLDER"
    secret_provider_plan_ref: str = "SECRET_PROVIDER_PLAN_REF_PLACEHOLDER"
    storage_provider_plan_ref: str = "STORAGE_PROVIDER_PLAN_REF_PLACEHOLDER"
    postgres_runtime_plan_ref: str = "POSTGRES_RUNTIME_PLAN_REF_PLACEHOLDER"
    hosted_deployment_plan_ref: str = "HOSTED_DEPLOYMENT_PLAN_REF_PLACEHOLDER"
    https_webhook_plan_ref: str = "HTTPS_WEBHOOK_PLAN_REF_PLACEHOLDER"
    sandbox_smoke_evidence_ref: str = "SANDBOX_SMOKE_EVIDENCE_REF_PLACEHOLDER"
    sandbox_read_validation_evidence_ref: str = (
        "SANDBOX_READ_VALIDATION_EVIDENCE_REF_PLACEHOLDER"
    )
    sandbox_evidence_linkage_ref: str = "SANDBOX_EVIDENCE_LINKAGE_REF_PLACEHOLDER"
    pilot_readiness_ref: str = "PILOT_READINESS_REF_PLACEHOLDER"
    pilot_approval_packet_ref: str = "PILOT_APPROVAL_PACKET_REF_PLACEHOLDER"
    rollback_plan_ref: str = "ROLLBACK_PLAN_REF_PLACEHOLDER"
    disable_plan_ref: str = "DISABLE_PLAN_REF_PLACEHOLDER"
    diagnostics_plan_ref: str = "DIAGNOSTICS_PLAN_REF_PLACEHOLDER"
    support_bundle_plan_ref: str = "SUPPORT_BUNDLE_PLAN_REF_PLACEHOLDER"
    monitoring_plan_ref: str = "MONITORING_PLAN_REF_PLACEHOLDER"
    incident_response_ref: str = "INCIDENT_RESPONSE_REF_PLACEHOLDER"
    data_handling_ref: str = "DATA_HANDLING_REF_PLACEHOLDER"
    reviewer_placeholder: str = "DRY_RUN_REVIEWER_PLACEHOLDER"
    expiry_placeholder: str = "DRY_RUN_EXPIRY_PLACEHOLDER"
    known_limitations: list[str] = Field(
        default_factory=lambda: ["KNOWN_LIMITATION_PLACEHOLDER"]
    )
    notes: list[str] = Field(default_factory=lambda: ["REFS_ONLY_PLACEHOLDER"])


class HostedPilotDryRunReport(StrictHostedPilotDryRunModel):
    profile_name: str
    status: HostedPilotDryRunStatus
    decision: HostedPilotDryRunDecision
    refs_total: int
    required_refs_present: int
    missing_refs: list[str] = Field(default_factory=list)
    blocker_summary: list[str] = Field(default_factory=list)
    requirements: list[HostedPilotDryRunRequirement] = Field(default_factory=list)
    evidence_refs: list[HostedPilotDryRunEvidenceRef] = Field(default_factory=list)
    dry_run_execution_attempted: bool = False
    live_operation_attempted: bool = False
    deployment_attempted: bool = False
    procore_call_attempted: bool = False
    db_connection_attempted: bool = False
    cloud_call_attempted: bool = False
    webhook_registration_attempted: bool = False
    report_contents_exposed: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    findings: list[HostedPilotDryRunFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class HostedPilotDryRunArtifactResult(StrictHostedPilotDryRunModel):
    profile_name: str
    output_directory: str
    files: list[str]
    live_operations: bool = False
    deployment_attempted: bool = False
    private_values_exposed: bool = False
