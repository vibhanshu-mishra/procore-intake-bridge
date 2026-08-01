from enum import StrEnum

from pydantic import BaseModel, Field


class ReleaseCandidateStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class ReleaseCandidateDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "release_candidate_ready_for_maintainer_review"
    NEEDS_REVIEW = "release_candidate_needs_review"
    BLOCKED = "release_candidate_blocked"
    NOT_RUN = "release_candidate_not_run"


class ReleaseCandidateDomain(StrEnum):
    VERSION_METADATA = "version_metadata"
    PACKAGE_METADATA = "package_metadata"
    SETUP_EXPERIENCE = "setup_experience"
    DEMO_SEED_RESET = "demo_seed_reset"
    API_DOCUMENTATION = "api_documentation"
    HOSTED_UI_PREPARATION = "hosted_ui_preparation"
    DOCS_SITE_POLISH = "docs_site_polish"
    SECURITY_READINESS = "security_readiness"
    SECURITY_GAP_CLOSEOUT = "security_gap_closeout"
    PUBLIC_REPO_SAFETY = "public_repo_safety"
    ROUTE_BOUNDARY = "route_boundary"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"
    CHANGELOG_AND_ROADMAP = "changelog_and_roadmap"
    RELEASE_BOUNDARY = "release_boundary"
    PRIVATE_REVIEW_BOUNDARY = "private_review_boundary"


class ReleaseCandidateGateStatus(StrEnum):
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class ReleaseCandidateFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: ReleaseCandidateDomain | None = None


class ReleaseCandidateDomainSummary(BaseModel):
    domain: ReleaseCandidateDomain
    status: ReleaseCandidateGateStatus
    summary: str
    source: str
    public_safe: bool = True
    private_review_required: bool = False


class ReleaseCandidateGate(BaseModel):
    code: str
    domain: ReleaseCandidateDomain
    status: ReleaseCandidateGateStatus
    description: str
    evidence: list[str] = Field(default_factory=list)
    required: bool = True


class ReleaseCandidateGap(BaseModel):
    code: str
    domain: ReleaseCandidateDomain
    description: str
    private_review_required: bool = False
    blocking: bool = False


class ReleaseCandidateCommandPlanItem(BaseModel):
    command: str
    purpose: str
    domain: ReleaseCandidateDomain
    safe_read_only: bool = True
    writes_generated_output: bool = False
    database_access: bool = False
    live_operation: bool = False
    external_operation: bool = False


class ReleaseCandidateMatrixItem(BaseModel):
    domain: ReleaseCandidateDomain
    gate_status: ReleaseCandidateGateStatus
    evidence: str
    gap: str
    next_step: str


class ReleaseCandidateReport(BaseModel):
    status: ReleaseCandidateStatus
    decision: ReleaseCandidateDecision
    target_version: str
    dependencies: dict[str, bool] = Field(default_factory=dict)
    domain_summaries: list[ReleaseCandidateDomainSummary] = Field(default_factory=list)
    gates: list[ReleaseCandidateGate] = Field(default_factory=list)
    gaps: list[ReleaseCandidateGap] = Field(default_factory=list)
    command_plan: list[ReleaseCandidateCommandPlanItem] = Field(default_factory=list)
    matrix: list[ReleaseCandidateMatrixItem] = Field(default_factory=list)
    domains_total: int
    domains_passed: int
    domains_needing_review: int
    domains_blocked: int
    gates_total: int
    gates_passed: int
    gates_needing_review: int
    gaps_total: int
    findings: list[ReleaseCandidateFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    public_repo_safe_for_rc_review: bool
    private_review_required: bool = True
    package_build_attempted: bool = False
    docker_build_attempted: bool = False
    publish_attempted: bool = False
    tag_attempted: bool = False
    release_attempted: bool = False
    deploy_attempted: bool = False
    docs_deploy_attempted: bool = False
    workflow_changed: bool = False
    github_api_attempted: bool = False
    package_registry_call_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    production_approval_granted: bool = False
    release_approval_granted: bool = False
    pilot_approval_granted: bool = False
    deployment_approval_granted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class ReleaseCandidateArtifactResult(BaseModel):
    status: ReleaseCandidateStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    package_build: bool = False
    docker_build: bool = False
    publish: bool = False
    tag: bool = False
    release: bool = False
    deploy: bool = False
