"""Public-safe, offline maintainer handoff models for Phase J9.

These models describe review material only.  They deliberately carry explicit
negative operation/approval flags so a generated report cannot be mistaken for
a release, deployment, or production authorization.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class MaintainerHandoffStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class MaintainerHandoffDecision(StrEnum):
    READY_FOR_REVIEW = "maintainer_handoff_ready_for_review"
    READY_FOR_MAINTAINER_REVIEW = "maintainer_handoff_ready_for_review"
    NEEDS_REVIEW = "maintainer_handoff_needs_review"
    BLOCKED = "maintainer_handoff_blocked"
    NOT_RUN = "maintainer_handoff_not_run"


class MaintainerHandoffDomain(StrEnum):
    REPOSITORY_OVERVIEW = "repository_overview"
    LOCAL_SETUP = "local_setup"
    DEMO_MODE = "demo_mode"
    API_DOCUMENTATION = "api_documentation"
    PRODUCT_UI = "product_ui"
    HOSTED_PREPARATION = "hosted_preparation"
    SECURITY_READINESS = "security_readiness"
    PRIVACY_SECURITY_GAPS = "privacy_security_gaps"
    RELEASE_HANDOFF = "release_handoff"
    KNOWN_LIMITATIONS = "known_limitations"
    PRIVATE_REVIEW_BOUNDARY = "private_review_boundary"
    MAINTAINER_DECISION = "maintainer_decision"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"
    PUBLIC_SAFETY = "public_safety"


class MaintainerHandoffGateStatus(StrEnum):
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class MaintainerHandoffFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: MaintainerHandoffDomain | None = None
    source: str | None = None


class MaintainerHandoffDomainSummary(BaseModel):
    domain: MaintainerHandoffDomain
    status: MaintainerHandoffGateStatus
    summary: str
    source: str
    public_safe: bool = True
    private_review_required: bool = False


class MaintainerHandoffGate(BaseModel):
    code: str
    domain: MaintainerHandoffDomain
    status: MaintainerHandoffGateStatus
    description: str
    evidence: list[str] = Field(default_factory=list)
    required: bool = True


class MaintainerCommandPlanItem(BaseModel):
    command: str
    purpose: str
    domain: MaintainerHandoffDomain
    safe_read_only: bool = True
    writes_generated_output: bool = False
    database_access: bool = False
    live_operation: bool = False
    external_operation: bool = False


class MaintainerReviewChecklistItem(BaseModel):
    code: str
    description: str
    domain: MaintainerHandoffDomain = MaintainerHandoffDomain.MAINTAINER_DECISION
    required: bool = True
    evidence: str = ""
    decision_required: bool = True
    private_review_required: bool = False


class MaintainerDecisionLogItem(BaseModel):
    code: str
    question: str
    placeholder: str = "REVIEW_DECISION_PLACEHOLDER"
    owner: str = "maintainer"
    domain: MaintainerHandoffDomain = MaintainerHandoffDomain.MAINTAINER_DECISION
    required: bool = True
    private_review_required: bool = False


class MaintainerHandoffMatrixItem(BaseModel):
    domain: MaintainerHandoffDomain
    gate_status: MaintainerHandoffGateStatus
    evidence: str
    included_scope: str
    not_included: str
    next_step: str

    @property
    def limitation(self) -> str:
        """Compatibility alias used by matrix consumers from earlier phases."""

        return self.not_included


class MaintainerHandoffReport(BaseModel):
    status: MaintainerHandoffStatus
    decision: MaintainerHandoffDecision
    target_version: str
    dependencies: dict[str, bool] = Field(default_factory=dict)
    domain_summaries: list[MaintainerHandoffDomainSummary] = Field(default_factory=list)
    gates: list[MaintainerHandoffGate] = Field(default_factory=list)
    quickstart: list[str] = Field(default_factory=list)
    included_scope: list[str] = Field(default_factory=list)
    not_included_scope: list[str] = Field(default_factory=list)
    review_checklist: list[MaintainerReviewChecklistItem] = Field(default_factory=list)
    command_plan: list[MaintainerCommandPlanItem] = Field(default_factory=list)
    decision_log_template: list[MaintainerDecisionLogItem] = Field(default_factory=list)
    handoff_matrix: list[MaintainerHandoffMatrixItem] = Field(default_factory=list)
    findings: list[MaintainerHandoffFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    domains_total: int = 0
    domains_passed: int = 0
    domains_needing_review: int = 0
    domains_blocked: int = 0
    gates_total: int = 0
    gates_passed: int = 0
    gates_needing_review: int = 0
    checklist_items_total: int = 0
    command_plan_items_total: int = 0
    decision_log_items_total: int = 0
    matrix_items_total: int = 0
    public_repo_safe_for_handoff: bool = True
    maintainer_decision_required: bool = True
    private_review_required: bool = True
    actual_release_performed: bool = False
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
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    package_publication_claimed: bool = False
    docs_hosting_claimed: bool = False
    private_report_contents_exposed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)

    @property
    def maintainer_quickstart(self) -> list[str]:
        return self.quickstart

    @property
    def included(self) -> list[str]:
        return self.included_scope

    @property
    def not_included(self) -> list[str]:
        return self.not_included_scope

    @property
    def maintainer_review_checklist(self) -> list[MaintainerReviewChecklistItem]:
        return self.review_checklist

    @property
    def maintainer_command_plan(self) -> list[MaintainerCommandPlanItem]:
        return self.command_plan

    @property
    def maintainer_decision_log(self) -> list[MaintainerDecisionLogItem]:
        return self.decision_log_template

    @property
    def matrix(self) -> list[MaintainerHandoffMatrixItem]:
        return self.handoff_matrix


class MaintainerHandoffArtifactResult(BaseModel):
    status: MaintainerHandoffStatus
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
