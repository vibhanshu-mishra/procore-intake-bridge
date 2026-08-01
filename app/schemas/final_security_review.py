from enum import StrEnum

from pydantic import BaseModel, Field


class FinalSecurityReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_PRIVATE_SECURITY_REVIEW = "needs_private_security_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class FinalSecurityDecision(StrEnum):
    READY_FOR_PRIVATE_REVIEW = "final_security_ready_for_private_review"
    NEEDS_PRIVATE_REVIEW = "final_security_needs_private_review"
    BLOCKED = "final_security_blocked"
    NOT_RUN = "final_security_not_run"


class FinalSecurityDomain(StrEnum):
    THREAT_MODEL = "threat_model"
    AUTH_PERMISSION_BOUNDARY = "auth_permission_boundary"
    WEBHOOK_SECURITY = "webhook_security"
    DATA_RETENTION_REDACTION = "data_retention_redaction"
    SECRETS_STORAGE_DATABASE = "secrets_storage_database"
    DEPENDENCY_SUPPLY_CHAIN = "dependency_supply_chain"
    INCIDENT_RESPONSE_FORENSICS = "incident_response_forensics"
    PUBLIC_REPO_SAFETY = "public_repo_safety"
    ROUTE_BOUNDARY = "route_boundary"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"
    DEMO_MODE_BOUNDARY = "demo_mode_boundary"
    SANDBOX_PILOT_BOUNDARY = "sandbox_pilot_boundary"
    RELEASE_READINESS_BOUNDARY = "release_readiness_boundary"
    PRIVATE_SECURITY_REVIEW_BOUNDARY = "private_security_review_boundary"


class FinalSecurityGateStatus(StrEnum):
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class FinalSecurityFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: FinalSecurityDomain | None = None


class FinalSecurityDomainSummary(BaseModel):
    domain: FinalSecurityDomain
    status: FinalSecurityGateStatus
    summary: str
    private_review_required: bool = False


class FinalSecurityGate(BaseModel):
    name: str
    domain: FinalSecurityDomain
    status: FinalSecurityGateStatus
    description: str
    evidence_paths: list[str] = Field(default_factory=list)


class FinalSecurityReviewDependency(BaseModel):
    name: str
    path: str
    domain: FinalSecurityDomain
    required: bool = True
    present: bool


class FinalSecurityGap(BaseModel):
    code: str
    domain: FinalSecurityDomain
    description: str
    private_review_required: bool = True
    blocking: bool = False


class FinalSecurityReport(BaseModel):
    status: FinalSecurityReviewStatus
    decision: FinalSecurityDecision
    domains_total: int
    domains_passed: int
    domains_needing_review: int
    domains_blocked: int
    gates_total: int
    gates_passed: int
    gates_needing_review: int
    gaps_total: int
    private_review_required: bool = True
    public_repo_safe_for_maintainer_review: bool = False
    production_approval_granted: bool = False
    pilot_approval_granted: bool = False
    release_approval_granted: bool = False
    security_certification_claimed: bool = False
    legal_compliance_claimed: bool = False
    live_operation_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_connection_attempted: bool = False
    scanner_attempted: bool = False
    notification_attempted: bool = False
    deployment_attempted: bool = False
    release_attempted: bool = False
    package_build_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    raw_payloads_exposed: bool = False
    raw_logs_exposed: bool = False
    urls_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    storage_keys_exposed: bool = False
    attachment_contents_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    findings: list[FinalSecurityFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dependencies: list[FinalSecurityReviewDependency] = Field(default_factory=list)
    domain_summaries: list[FinalSecurityDomainSummary] = Field(default_factory=list)
    gates: list[FinalSecurityGate] = Field(default_factory=list)
    gaps: list[FinalSecurityGap] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class FinalSecurityArtifactResult(BaseModel):
    status: FinalSecurityReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    external_operations: bool = False
    approval_operations: bool = False
